# Load testing with k6

k6 load tests for the feed endpoint (`GET /api/v1/feed`) of the API gateway
(Issue #17). The test measures p50/p95/p99 latency, throughput, and error
rate against the target SLOs and fails (non-zero exit code) if any SLO
threshold is breached, which makes it directly usable as a CI gate.

## Files

| File | Purpose |
|------|---------|
| `feed_load_test.js` | k6 script: ramp-up, steady-state, and spike scenarios |
| `config.json` | Tunable defaults: base URL, SLO targets, scenario shapes |

## Test phases

The three scenarios run back-to-back (offset via `startTime`):

1. **ramp_up** — `ramping-vus` from 0 to 1000 concurrent VUs over 2 minutes,
   then holds 1 minute at 1000 VUs. Warms server-side caches.
2. **steady_state** — `constant-arrival-rate` injecting 1100 req/s
   (above the 1000 req/s SLO) for 5 minutes with up to 1200 VUs. If the
   system cannot sustain the rate, k6 records `dropped_iterations` and the
   throughput threshold fails.
3. **spike** — sharp `ramping-vus` burst: 0 to 1000 VUs in 10 seconds,
   30 seconds hold, 10 seconds ramp-down.

Traffic is split 80/20 between a deterministic pool of 50 "warm" user IDs
(repeat requests, cache-hit path, tagged `cache:warm`) and random UUIDs
(cache-miss path, tagged `cache:cold`).

## SLO thresholds

| Metric | Target | k6 threshold |
|--------|--------|--------------|
| p50 latency (cached) | < 30 ms | `http_req_duration{cache:warm}: p(50)<30` |
| p99 latency (cold) | < 80 ms | `http_req_duration{cache:cold}: p(99)<80` |
| p95 latency (all traffic) | < 80 ms | `http_req_duration: p(95)<80` |
| Error rate | < 0.1 % | `http_req_failed: rate<0.001` |
| Throughput | > 1000 req/s | `dropped_iterations{scenario:steady_state}: count<1` |

Targets are read from `config.json` (`slo` block), so they can be tuned
without touching the script.

## Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000` (from `config.json`) | Base URL of the API gateway |
| `TOKEN` | *(empty)* | JWT bearer token, sent as `Authorization: Bearer <TOKEN>`. Required — the feed route enforces JWT auth; without it every request is a 401 and the error-rate threshold fails. |
| `SMOKE` | *(unset)* | Any non-empty value shrinks all phases to a ~40 s, low-VU functional sanity run |

## How to run

### Native k6

Install k6 (<https://grafana.com/docs/k6/latest/set-up/install-k6/>), then:

```bash
k6 run -e BASE_URL=http://localhost:8000 -e TOKEN="$JWT" tests/load/feed_load_test.js
```

Quick smoke run (seconds instead of ~10 minutes):

```bash
k6 run -e SMOKE=true -e TOKEN="$JWT" tests/load/feed_load_test.js
```

### Docker (grafana/k6)

```bash
docker run --rm -i --network host --user "$(id -u):$(id -g)" \
  -v "$PWD/tests/load:/scripts" -w /scripts \
  -e BASE_URL=http://localhost:8000 -e TOKEN="$JWT" \
  grafana/k6 run feed_load_test.js
```

`--user` makes the container able to write `summary.json` into the mounted
directory. `--network host` lets the container reach a gateway on `localhost`. When
targeting the docker-compose stack from another network, use
`-e BASE_URL=http://api-gateway:8000 --network <compose-network>` instead.

### Makefile targets

```bash
make test-load                       # native k6 against localhost:8000
make test-load-smoke                 # quick sanity run
make test-load-docker                # via grafana/k6 container
make test-load TOKEN=$JWT BASE_URL=http://staging.example.com
```

## Output / CI integration

- The script's `handleSummary` writes **`summary.json`** (full k6 end-of-test
  summary, all metrics and threshold results) to the working directory and
  prints a compact SLO report to stdout.
- k6 exits non-zero when any threshold fails, so the run can gate a pipeline
  directly.
- For streaming per-request metrics (time-series analysis, Grafana, etc.):

```bash
k6 run --out json=results.json tests/load/feed_load_test.js
```

## Generating a token

The gateway validates JWTs via `services/api-gateway/src/auth/jwt_handler.py`
(HS256, `JWT_SECRET`, defaults to the dev secret). Options:

- **Local/dev:** the handler accepts the literal token `dev-token` as a
  bypass, so `TOKEN=dev-token` works out of the box against a dev gateway.
- **Real JWT:** mint one with the gateway's own helper:

  ```bash
  python -c "from uuid import uuid4; \
    from services.api_gateway.src.auth.jwt_handler import create_access_token; \
    print(create_access_token(uuid4()))"
  ```

  Set `JWT_SECRET` to match the target environment.

## Caveat: gateway rate limiting

`RateLimiterMiddleware` allows **60 req/min per Authorization header** (or per
client IP when unauthenticated). All VUs share one `TOKEN`, therefore one
bucket — an unmodified dev gateway will answer almost everything with 429 and
the error-rate threshold will (correctly) fail. For meaningful load tests,
raise or disable the limiter in the target environment (e.g. bump
`requests_per_minute` where `RateLimiterMiddleware` is added in
`services/api-gateway/src/main.py`), or point the test at a deployment where
limits are enforced upstream per end-user.
