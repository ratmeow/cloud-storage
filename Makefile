.PHONY: test-local test-docker infra-up infra-down

infra-up:
	docker compose -f compose.test.yaml --env-file test.env up -d test-postgres test-redis test-minio

infra-down:
	docker compose -f compose.test.yaml --env-file test.env down

test-local: infra-up
	export $$(cat test.env | xargs) && pytest
	$(MAKE) infra-down

test-docker:
	docker compose -f compose.test.yaml --env-file test.env --profile full up --build --abort-on-container-exit test-backend
	docker compose -f compose.test.yaml --env-file test.env down