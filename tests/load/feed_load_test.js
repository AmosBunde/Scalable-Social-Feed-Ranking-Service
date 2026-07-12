/**
 * k6 load test for GET /api/v1/feed (Issue #17).
 *
 * Phases (scenarios), run back-to-back:
 *   1. ramp_up      - ramping-vus 0 -> 1000 VUs, then hold (warms caches).
 *   2. steady_state - constant-arrival-rate above the 1000 req/s SLO target;
 *                     this is the phase throughput is asserted on.
 *   3. spike        - sharp ramp to 1000 VUs to observe behaviour under a
 *                     sudden burst, then fast ramp-down.
 *
 * Traffic model: a deterministic pool of "warm" user IDs is requested
 * repeatedly (cache hits), while a configurable share of requests uses a
 * random user ID ("cold", cache miss). Requests are tagged cache:warm /
 * cache:cold so SLO thresholds can target each population separately.
 *
 * SLO thresholds (from tests/load/config.json):
 *   - p50 latency (cached/warm)  < 30ms
 *   - p99 latency (cold)         < 80ms
 *   - error rate                 < 0.1%
 *   - throughput (steady_state)  > 1000 req/s (no dropped iterations)
 *
 * Environment variables:
 *   BASE_URL - target base URL (default: config.baseUrl, http://localhost:8000)
 *   TOKEN    - JWT bearer token; sent as "Authorization: Bearer <TOKEN>"
 *   SMOKE    - if set (any non-empty value), shrinks all scenarios to a few
 *              VUs / seconds for a quick functional sanity check.
 *
 * Output: writes summary.json (full k6 summary data) for CI integration and
 * prints a compact SLO report to stdout. For streaming per-request metrics
 * use: k6 run --out json=results.json tests/load/feed_load_test.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';
import { Rate } from 'k6/metrics';

const config = JSON.parse(open('./config.json'));

const BASE_URL = __ENV.BASE_URL || config.baseUrl;
const TOKEN = __ENV.TOKEN || '';
const SMOKE = Boolean(__ENV.SMOKE);

const slo = config.slo;
const feedCfg = config.feed;

// Custom rate: 1 = request failed or returned a bad payload.
const feedErrors = new Rate('feed_errors');

// Deterministic warm pool, identical in every VU, so repeated requests for
// the same user IDs actually exercise the cache-hit path server-side.
const warmUserIds = Array.from({ length: feedCfg.warmUserPoolSize }, (_, i) =>
  `00000000-0000-4000-8000-${String(i + 1).padStart(12, '0')}`
);

/** RFC 4122-ish v4 UUID (no external deps so the script is fully offline). */
function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function buildScenarios() {
  if (SMOKE) {
    return {
      ramp_up: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
          { duration: '5s', target: 5 },
          { duration: '5s', target: 5 },
        ],
        gracefulRampDown: '5s',
        tags: { phase: 'ramp_up' },
      },
      steady_state: {
        executor: 'constant-arrival-rate',
        rate: 10,
        timeUnit: '1s',
        duration: '10s',
        preAllocatedVUs: 10,
        maxVUs: 20,
        startTime: '15s',
        tags: { phase: 'steady_state' },
      },
      spike: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
          { duration: '2s', target: 10 },
          { duration: '5s', target: 10 },
          { duration: '2s', target: 0 },
        ],
        startTime: '30s',
        tags: { phase: 'spike' },
      },
    };
  }

  const ramp = config.scenarios.rampUp;
  const steady = config.scenarios.steadyState;
  const spike = config.scenarios.spike;

  // Scenario start offsets: each phase begins when the previous one ends.
  const steadyStart = addDurations(ramp.rampDuration, ramp.holdDuration);
  const spikeStart = addDurations(steadyStart, steady.duration);

  return {
    // Phase 1: gradual ramp to 1000 concurrent VUs, then hold.
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: ramp.startVus,
      stages: [
        { duration: ramp.rampDuration, target: ramp.targetVus },
        { duration: ramp.holdDuration, target: ramp.targetVus },
      ],
      gracefulRampDown: '30s',
      tags: { phase: 'ramp_up' },
    },
    // Phase 2: fixed request rate above the throughput SLO. If the system
    // cannot sustain it, k6 reports dropped_iterations (thresholded below).
    steady_state: {
      executor: 'constant-arrival-rate',
      rate: steady.rate,
      timeUnit: '1s',
      duration: steady.duration,
      preAllocatedVUs: steady.preAllocatedVus,
      maxVUs: steady.maxVus,
      startTime: steadyStart,
      tags: { phase: 'steady_state' },
    },
    // Phase 3: sudden burst to full concurrency.
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: spike.spikeUpDuration, target: spike.targetVus },
        { duration: spike.holdDuration, target: spike.targetVus },
        { duration: spike.spikeDownDuration, target: 0 },
      ],
      startTime: spikeStart,
      tags: { phase: 'spike' },
    },
  };
}

/** Add simple k6 durations ("2m", "30s", "1m30s") and return "<n>s". */
function addDurations(...durations) {
  let totalSeconds = 0;
  for (const d of durations) {
    const re = /(\d+)([hms])/g;
    let m;
    while ((m = re.exec(d)) !== null) {
      const n = parseInt(m[1], 10);
      totalSeconds += m[2] === 'h' ? n * 3600 : m[2] === 'm' ? n * 60 : n;
    }
  }
  return `${totalSeconds}s`;
}

export const options = {
  scenarios: buildScenarios(),
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(50)', 'p(90)', 'p(95)', 'p(99)'],
  thresholds: {
    // Error rate SLO: < 0.1% across the whole run.
    http_req_failed: [`rate<${slo.maxErrorRate}`],
    feed_errors: [`rate<${slo.maxErrorRate}`],
    // Latency SLOs: p50 for cache-hit traffic, p99 for cache-miss traffic.
    'http_req_duration{cache:warm}': [`p(50)<${slo.p50CachedMs}`],
    'http_req_duration{cache:cold}': [`p(99)<${slo.p99ColdMs}`],
    // Overall p95 guard-rail across all phases.
    http_req_duration: [`p(95)<${slo.p99ColdMs}`],
    // Throughput SLO: the steady_state scenario injects > minThroughputRps;
    // any dropped iterations mean the target rate could not be sustained.
    'dropped_iterations{scenario:steady_state}': ['count<1'],
    checks: ['rate>0.999'],
  },
};

const requestParams = (cacheTag) => ({
  headers: Object.assign(
    { 'Content-Type': 'application/json' },
    TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}
  ),
  tags: { cache: cacheTag, endpoint: 'feed' },
});

export default function () {
  const warm = Math.random() < feedCfg.warmTrafficShare;
  const userId = warm
    ? warmUserIds[(Math.random() * warmUserIds.length) | 0]
    : uuidv4();

  const url = `${BASE_URL}${feedCfg.path}?user_id=${userId}&limit=${feedCfg.limit}`;
  const res = http.get(url, requestParams(warm ? 'warm' : 'cold'));

  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'body has posts array': (r) => {
      try {
        return Array.isArray(r.json('posts'));
      } catch (_e) {
        return false;
      }
    },
  });
  feedErrors.add(!ok);

  // Think-time for VU-based scenarios only. The arrival-rate scenario paces
  // itself and must not sleep, or the injected request rate would drop.
  if (exec.scenario.name !== 'steady_state') {
    sleep(0.5 + Math.random());
  }
}

/**
 * Machine-readable summary for CI plus a compact human-readable SLO report.
 * summary.json is written to the current working directory (mount the
 * directory read-write when running via Docker).
 */
export function handleSummary(data) {
  const m = data.metrics;
  const get = (name, stat) =>
    m[name] && m[name].values && m[name].values[stat] !== undefined
      ? m[name].values[stat]
      : null;
  const fmtMs = (v) => (v === null ? 'n/a' : `${v.toFixed(2)}ms`);
  const fmtPct = (v) => (v === null ? 'n/a' : `${(v * 100).toFixed(3)}%`);

  const lines = [
    '',
    '=== Feed load test: SLO report ===',
    `requests total:        ${get('http_reqs', 'count')}`,
    `throughput (overall):  ${(get('http_reqs', 'rate') || 0).toFixed(1)} req/s`,
    `p50 warm (SLO <${slo.p50CachedMs}ms):  ${fmtMs(get('http_req_duration{cache:warm}', 'p(50)'))}`,
    `p99 cold (SLO <${slo.p99ColdMs}ms):  ${fmtMs(get('http_req_duration{cache:cold}', 'p(99)'))}`,
    `p95 all:               ${fmtMs(get('http_req_duration', 'p(95)'))}`,
    `p99 all:               ${fmtMs(get('http_req_duration', 'p(99)'))}`,
    `error rate (SLO <${(slo.maxErrorRate * 100).toFixed(1)}%): ${fmtPct(get('http_req_failed', 'rate'))}`,
    `dropped iterations:    ${get('dropped_iterations', 'count') || 0}`,
    '==================================',
    '',
  ];

  return {
    'summary.json': JSON.stringify(data, null, 2),
    stdout: lines.join('\n'),
  };
}
