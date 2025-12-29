.PHONY: help install dev test clean run

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

dev: ## Lance le serveur en mode développement
	./venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000

test: ## Exécute les tests
	./venv/bin/pytest -v

clean: ## Nettoie les fichiers temporaires et la base de données
	rm -rf __pycache__ .pytest_cache
	rm -f data.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

run: ## Lance le serveur (production-like)
	./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
