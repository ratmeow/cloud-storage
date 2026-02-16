.PHONY: test-local test-docker infra-up infra-down start-app
.PHONY: dev-infra-up dev-infra-down dev-infra-logs dev-run dev-local dev-docker
.PHONY: prod-up prod-down

test-infra-up:
	docker compose -f compose.test.yaml --env-file test.env up -d test-postgres test-redis test-minio

test-infra-down:
	docker compose -f compose.test.yaml --env-file test.env down

test-local: infra-up
	export $$(cat test.env | xargs) && pytest
	$(MAKE) infra-down

test-docker:
	docker compose -f compose.test.yaml --env-file test.env --profile full up --build --abort-on-container-exit test-backend
	docker compose -f compose.test.yaml --env-file test.env down

dev-infra-up:
	docker compose -f compose.dev.yaml --env-file dev.env up -d dev-postgres dev-redis dev-minio

dev-infra-down:
	docker compose -f compose.dev.yaml --env-file dev.env down

dev-run:
	docker compose -f compose.dev.yaml --env-file dev.env up --build dev-backend

start-app:
	export $$(cat dev.env | xargs) && alembic upgrade head && uvicorn cloud_storage.main:create_app --port 8080
