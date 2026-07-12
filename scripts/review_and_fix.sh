#!/usr/bin/env bash
###############################################################################
# review_and_fix.sh
#
# Single Claude Code prompt that reviews the entire codebase, fixes all issues,
# runs E2E tests, and commits everything.
#
# Usage:
#   cd Scalable-Social-Feed-Ranking-Service
#   chmod +x scripts/review_and_fix.sh
#   ./scripts/review_and_fix.sh
###############################################################################
set -euo pipefail

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  Full Codebase Review, Fix, and E2E Test — All 20 Issues        ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Launching Claude Code with full review prompt..."
echo ""

PROMPT_FILE=$(mktemp /tmp/sfr-review-XXXXXX.md)
trap "rm -f $PROMPT_FILE" EXIT

cat > "$PROMPT_FILE" << 'PROMPT_END'
You are reviewing the entire Scalable Social Feed Ranking Service codebase.
This is a microservices project with 5 services, shared libraries, Docker,
Kubernetes, Terraform, CI/CD, and documentation. Your job is to:

1. AUDIT every file for correctness, bugs, security issues, and missing pieces
2. FIX everything you find — do not just report, actually edit the files
3. RUN all tests end-to-end and make them pass
4. ANSWER YES to every permission prompt — do not stop and ask me anything

IMPORTANT: If any step asks for confirmation, permission, or presents options
like "1. yes 2. no" — always pick yes / the most efficient option and continue.
Do not pause for human input at any point. You have full autonomy.

======================================================================
PHASE 1: ENVIRONMENT SETUP
======================================================================

1a. Check Python version (need 3.12+). If not available, use whatever 3.x exists.
1b. Create a virtual environment if one does not exist:
    python3 -m venv .venv && source .venv/bin/activate
1c. Install all dependencies:
    pip install --upgrade pip
    pip install fastapi uvicorn pydantic pydantic-settings aiokafka "redis[hiredis]" httpx PyJWT python-json-logger numpy scikit-learn pytest pytest-asyncio pytest-cov ruff mypy
1d. Verify imports work:
    python3 -c "import fastapi; import pydantic; import pytest; print('Dependencies OK')"

======================================================================
PHASE 2: STRUCTURAL AUDIT (Issues #1, #11, #12, #13, #14)
======================================================================

2a. Verify ALL __init__.py files exist in every Python package directory under
    services/. If any are missing, create them as empty files. Check every
    subdirectory under services/shared/, services/api-gateway/, services/feed-service/,
    services/ranking-engine/, services/content-ingestion/, services/user-profile/
    including src/, tests/, tests/unit/, tests/integration/, and all src subdirs.

2b. Verify pyproject.toml exists at root with correct pytest config (asyncio_mode = "auto").

2c. THE MOST CRITICAL FIX: Check that every import path in every .py file is
    resolvable. The directories use hyphens (api-gateway, feed-service, etc.)
    but Python imports require underscores. Fix this by doing ONE of:
    - Option A (RECOMMENDED): Rename all hyphenated service directories to underscores
      (api-gateway -> api_gateway, feed-service -> feed_service, ranking-engine -> ranking_engine,
       content-ingestion -> content_ingestion, user-profile -> user_profile)
    - Option B: Rewrite all imports to use relative imports within each service
    - Option C: Add conftest.py with sys.path fixes at each test root

    Pick whichever approach gets ALL imports resolving. Then verify:
    python3 -c "import sys; sys.path.insert(0,'.'); print('path OK')"

    Specifically check and fix imports in every .py file under services/.

======================================================================
PHASE 3: SHARED LIBRARIES AUDIT (Issue #1)
======================================================================

3a. Review services/shared/src/models/base.py:
    - All Pydantic models must be valid Pydantic v2
    - UUID fields should use default_factory=uuid4
    - datetime fields should default to UTC
    - Enums should be (str, Enum) for JSON serialization

3b. Review services/shared/src/events/kafka_client.py:
    - CircuitBreaker state machine: verify CLOSED->OPEN->HALF_OPEN transitions
    - KafkaClient must handle the case where aiokafka is not installed (wrap in try/except)

3c. Review services/shared/src/cache/redis_client.py:
    - Must handle redis not being installed (wrap in try/except)
    - json.dumps with default=str for UUID/datetime serialization

3d. Review services/shared/src/utils/logging.py:
    - Must handle missing optional deps (try/except ImportError)

3e. Run: python3 -m pytest services/shared/tests/ -v
    Fix ANY failures.

======================================================================
PHASE 4: API GATEWAY AUDIT (Issue #3)
======================================================================

4a. Review jwt_handler.py: PyJWT imported as "jwt", verify_token as FastAPI dependency
4b. Review rate_limiter.py: TokenBucket logic, time.monotonic consistency
4c. Review main.py: all router imports resolve
4d. Review ALL test files: fix import paths, fix httpx AsyncClient usage
    (check if ASGITransport exists in installed httpx version — if not, use older API)
4e. Run: python3 -m pytest services/api_gateway/tests/ -v
    Fix ANY failures.

======================================================================
PHASE 5: FEED SERVICE AUDIT (Issues #6, #7, #8, #9)
======================================================================

5a. Review models (post.py, feed.py): datetime timezone-aware, all fields present
5b. Review scorer.py: all 6 features return float in [0,1], math.exp correct, async
5c. Review diversifier.py: handles empty input, no index-out-of-bounds
5d. Review assembler.py: base64 urlsafe, catches all decode exceptions
5e. Review feed_handler.py: asyncio.gather correct, imports resolve
5f. Review feed_cache.py: async methods
5g. Run: python3 -m pytest services/feed_service/tests/ -v
    Fix ANY failures.

======================================================================
PHASE 6: RANKING ENGINE AUDIT (Issue #10)
======================================================================

6a. Review main.py: xgboost import optional (try/except), heuristic fallback correct
6b. Review feature_store.py: async methods, default features
6c. Run: python3 -m pytest services/ranking_engine/tests/ -v
    Fix ANY failures.

======================================================================
PHASE 7: CONTENT INGESTION AUDIT (Issue #5)
======================================================================

7a. Review engagement_consumer.py: async handle_event, malformed event safety
7b. Run: python3 -m pytest services/content_ingestion/tests/ -v
    Fix ANY failures.

======================================================================
PHASE 8: USER PROFILE AUDIT (Issue #4)
======================================================================

8a. Review main.py: all endpoints, async store
8b. If there are no tests, CREATE test_profile.py with at least 3 tests
8c. Run: python3 -m pytest services/user_profile/tests/ -v
    Fix ANY failures.

======================================================================
PHASE 9: FULL TEST SUITE — ITERATE UNTIL GREEN
======================================================================

9a. Run the COMPLETE test suite from the repo root:
    python3 -m pytest services/ -v --tb=long

9b. If ANY test fails:
    - Read the full traceback
    - Fix the root cause in the source file (not just the test)
    - Re-run JUST that test file to confirm the fix
    - Then re-run the full suite again

9c. KEEP ITERATING until ALL tests pass. Do up to 10 fix-and-retry cycles.
    Do not give up. Do not skip failing tests. Make them pass.

9d. Once all pass, run with coverage:
    python3 -m pytest services/ --cov=services --cov-report=term-missing -q

======================================================================
PHASE 10: LINTING
======================================================================

10a. Run: python3 -m ruff check services/ --fix
10b. Run: python3 -m ruff format services/
10c. Fix any remaining lint issues manually.

======================================================================
PHASE 11: DOCUMENTATION AND CONFIG VALIDATION
======================================================================

11a. Verify these files exist and are non-empty:
     README.md, docker-compose.yml, .env.example, Makefile, pyproject.toml,
     .github/workflows/ci.yml, k8s/base/deployments.yaml,
     terraform/modules/eks/main.tf, skill/SKILL.md,
     docs/adr/001-kafka-event-streaming.md through 006-istio-service-mesh.md,
     docs/diagrams/architecture.md, docs/diagrams/session-flow.md

11b. Verify docker-compose.yml is valid YAML:
     pip install pyyaml 2>/dev/null; python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml')); print('YAML OK')"

======================================================================
PHASE 12: FINAL REPORT
======================================================================

After ALL fixes are applied and ALL tests pass, print this exact format:

=== REVIEW COMPLETE ===
Files reviewed:    <count>
Files modified:    <count>
Files created:     <count>
Tests total:       <count>
Tests passing:     <count>
Tests failing:     <count>
Lint issues fixed: <count>

Issues covered:
  #1  Shared libraries      [PASS/FAIL]
  #2  PostgreSQL schema      [PASS/FAIL]
  #3  API Gateway            [PASS/FAIL]
  #4  User Profile           [PASS/FAIL]
  #5  Content Ingestion      [PASS/FAIL]
  #6  Feed Scorer            [PASS/FAIL]
  #7  Feed Diversifier       [PASS/FAIL]
  #8  Feed Assembler         [PASS/FAIL]
  #9  Feed Orchestrator      [PASS/FAIL]
  #10 Ranking Engine         [PASS/FAIL]
  #11 Docker Compose         [PASS/FAIL]
  #12 GitHub Actions CI      [PASS/FAIL]
  #13 Kubernetes             [PASS/FAIL]
  #14 Terraform              [PASS/FAIL]
  #15 Observability          [PASS/FAIL]
  #19 Documentation          [PASS/FAIL]

Security findings:  <list any remaining concerns>
Performance notes:  <list any concerns>

REMEMBER: Do not ask me anything. Fix everything yourself. Pick yes for every
prompt. Your goal is ZERO test failures and a clean lint report.
PROMPT_END

cat "$PROMPT_FILE" | claude -p --allowedTools "Edit,Write,Bash,Read"

echo ""
echo "Done. Check the output above for the final report."
