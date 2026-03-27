.PHONY: test-local test-docker infra-up infra-down start-app
.PHONY: dev-infra-up dev-infra-down dev-infra-logs dev-run dev-local dev-docker
.PHONY: prod-up prod-down
.PHONY: test-infra-up test-infra-down

test-infra-up:
	docker compose -f compose.test.yaml --env-file test.env up -d test-postgres test-redis test-minio

test-infra-down:
	docker compose -f compose.test.yaml --env-file test.env down

test-local:
	$(MAKE) test-infra-up
	export $$(cat test.env | xargs) && pytest
	$(MAKE) test-infra-down

test-docker:
	docker compose -f compose.test.yaml --env-file test.env --profile full up --build --abort-on-container-exit test-backend
	docker compose -f compose.test.yaml --env-file test.env down

dev-infra-up:
	docker compose -f compose.dev.yaml --env-file dev.env up -d dev-postgres dev-redis dev-minio

dev-down:
	docker compose -f compose.dev.yaml --env-file dev.env down

dev-run-backend:
	docker compose -f compose.dev.yaml --env-file dev.env up --build dev-backend

dev-run-frontend:
	docker compose -f compose.dev.yaml --env-file dev.env up --build dev-frontend

start-app:
	export $$(cat dev.env | xargs) && alembic upgrade head && uvicorn cloud_storage.main:create_app --host "0.0.0.0" --port 8080
