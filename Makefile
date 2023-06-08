.PHONY: test lint

test:
	poetry run pytest -vv  --log-cli-level=DEBUG tests/test_soracam_client.py

lint:
	poetry run flake8
