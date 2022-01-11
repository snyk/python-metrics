test:
	poetry run pytest --cov=snyk_metrics .

lint:
	poetry run pre-commit run

install-hooks:
	poetry run pre-commit install --install-hooks
