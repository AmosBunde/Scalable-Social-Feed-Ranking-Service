.PHONY: setup dev quickstart test test-unit test-integration test-e2e test-coverage test-load test-load-smoke test-load-docker lint build deploy-dev seed clean

# Load test configuration (override: make test-load BASE_URL=... TOKEN=...)
BASE_URL ?= http://localhost:8000
TOKEN ?= dev-token

# --- Setup ---
setup:
	@echo "Installing Python dependencies..."
	pip install -r requirements-dev.txt
	@echo "Setup complete."

# --- Development ---
dev:
	docker compose up -d
	@echo "Services starting... Check http://localhost:$${HOST_GATEWAY_PORT:-8000}/health"

# One command from clean checkout to a running, verified stack.
# Override host ports if taken: HOST_GATEWAY_PORT=18080 make quickstart
quickstart:
	docker compose up -d --build --wait
	@echo "Verifying gateway health..."
	@curl -sf http://localhost:$${HOST_GATEWAY_PORT:-8000}/health >/dev/null \
		&& echo "OK: gateway healthy"
	@curl -sf -H "Authorization: Bearer dev-token" \
		http://localhost:$${HOST_GATEWAY_PORT:-8000}/api/v1/feed >/dev/null \
		&& echo "OK: authenticated feed request served"
	@echo ""
	@echo "Stack is up:"
	@echo "  API gateway  http://localhost:$${HOST_GATEWAY_PORT:-8000}  (Bearer dev-token)"
	@echo "  Jaeger UI    http://localhost:$${HOST_JAEGER_UI_PORT:-16686}"
	@echo "  Grafana      http://localhost:$${HOST_GRAFANA_PORT:-3000}  (admin/admin)"
	@echo "  Prometheus   http://localhost:$${HOST_PROMETHEUS_PORT:-9090}"
	@echo "Stop with: make stop"

dev-logs:
	docker compose logs -f

stop:
	docker compose down

# --- Database ---
seed:
	@echo "Seeding sample data..."
	python scripts/seed_data.py

# --- Testing ---
test: test-unit test-integration

test-unit:
	python -m pytest services/*/tests/unit/ -v --tb=short

test-integration:
	docker compose -f docker-compose.test.yml up -d
	python -m pytest services/*/tests/integration/ -v --tb=short
	docker compose -f docker-compose.test.yml down

test-e2e:
	python -m pytest tests/e2e/ -v --tb=short

test-service:
	python -m pytest services/$(SVC)/tests/ -v --tb=short

test-coverage:
	python -m pytest services/ --cov=services --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

# --- Load Testing (see tests/load/README.md) ---
test-load:
	k6 run -e BASE_URL=$(BASE_URL) -e TOKEN=$(TOKEN) tests/load/feed_load_test.js

test-load-smoke:
	k6 run -e BASE_URL=$(BASE_URL) -e TOKEN=$(TOKEN) -e SMOKE=true tests/load/feed_load_test.js

test-load-docker:
	docker run --rm -i --network host --user $$(id -u):$$(id -g) \
		-v $(PWD)/tests/load:/scripts -w /scripts \
		-e BASE_URL=$(BASE_URL) -e TOKEN=$(TOKEN) grafana/k6 run feed_load_test.js

# --- Code Quality ---
lint:
	ruff check services/
	ruff format --check services/
	mypy services/ --ignore-missing-imports

format:
	ruff format services/
	ruff check --fix services/

# --- Build ---
build:
	docker compose build

build-service:
	docker compose build $(SVC)

# --- Deploy ---
deploy-dev:
	kubectl apply -k k8s/overlays/dev/

deploy-staging:
	kubectl apply -k k8s/overlays/staging/

deploy-prod:
	kubectl apply -k k8s/overlays/prod/

# --- Infrastructure ---
terraform-init:
	cd terraform/environments/$(ENV) && terraform init

terraform-plan:
	cd terraform/environments/$(ENV) && terraform plan

terraform-apply:
	cd terraform/environments/$(ENV) && terraform apply

# --- Cleanup ---
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage
