.PHONY: help build up down restart logs shell db-shell clean seed clear-db status dev prod
# Default target
help: ## Show this help message
	@echo "Interim App - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development commands
build: ## Build all Docker images (backend + frontend)
	docker compose build

up: ## Start all services (backend + frontend)
	docker compose up -d
	@echo "🚀 Services started!"
	@echo "📚 API: http://localhost:5000"
	@echo "📖 Swagger: http://localhost:5000/apidocs/"
	@echo "🗄️ Mongo Express: http://localhost:8081 (admin/admin123)"
	@echo "⚛️  React App: http://localhost:3000"

down: ## Stop all services (backend + frontend)
	docker compose down
	@echo "🛑 Services stopped!"

restart: ## Restart all services (backend + frontend)
	make down
	make up

dev: ## Start in development mode with logs (backend + frontend)
	docker compose up

prod: ## Start in production mode - detached (backend + frontend)
	docker compose -f docker-compose.yml up -d --build

# Logs and monitoring
logs: ## Show logs for all services (backend + frontend)
	docker compose logs -f

logs-backend: ## Show logs for backend service only
	docker compose logs -f backend

logs-frontend: ## Show logs for frontend service only
	docker compose logs -f frontend

logs-db: ## Show logs for MongoDB only
	docker compose logs -f mongodb

logs-mongo-express: ## Show logs for Mongo Express only
	docker compose logs -f mongo-express

# Shell access
shell: ## Access Flask app shell
	docker compose exec backend bash

shell-backend: ## Access backend container shell
	docker compose exec backend bash

shell-frontend: ## Access frontend container shell
	docker compose exec frontend sh

shell-db: ## Access MongoDB shell
	docker compose exec mongodb mongosh interim_app

db-shell: ## Access MongoDB shell (alternative)
	docker compose exec mongodb mongo interim_app

# Database management
seed: ## Seed database with mock data
	docker compose exec backend python scripts/seed_db.py

seed-local: ## Seed database with mock data (local)
	cd backend && python scripts/seed_db.py

clear-db: ## Clear all data from database
	docker compose exec backend python scripts/clear_db.py

clear-db-local: ## Clear all data from database (local)
	cd backend && python scripts/clear_db.py

reset-db: ## Clear database and seed with fresh data
	make clear-db
	make seed

reset-db-local: ## Clear database and seed with fresh data (local)
	make clear-db-local
	make seed-local

# Status and information
status: ## Show status of all services (backend + frontend)
	docker compose ps

images: ## Show Docker images
	docker compose images

# Cleanup commands
clean: ## Remove containers and volumes
	docker compose down -v
	docker compose rm -f

clean-all: ## Remove everything (containers, volumes, images)
	docker compose down -v --rmi all
	docker system prune -f

# Testing
test: ## Run backend tests
	docker compose exec backend python -m pytest

test-local: ## Run backend tests locally
	cd backend && python -m pytest

test-coverage: ## Run tests with coverage
	docker compose exec backend python -m pytest --cov=app --cov-report=html

test-coverage-local: ## Run tests with coverage locally
	cd backend && python -m pytest --cov=app --cov-report=html

test-frontend: ## Run frontend tests
	docker compose exec frontend npm test

test-all: ## Run all tests (backend + frontend)
	make test
	make test-frontend

test-all-local: ## Run all tests locally
	make test-local
	make test-frontend

# Utility commands
rebuild: ## Rebuild and restart everything (backend + frontend)
	make clean
	make build
	make up

fresh-start: ## Complete fresh start with new data (backend + frontend)
	make clean
	make build
	make up
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	make seed
	@echo "✅ Fresh installation complete!"

# Database backup and restore
backup-db: ## Backup database to file
	docker compose exec mongodb mongodump --db interim_app --out /data/backup
	docker cp $$(docker compose ps -q mongodb):/data/backup ./backup_$$(date +%Y%m%d_%H%M%S)
	@echo "💾 Database backed up!"

# Check health
health: ## Check health of all services (backend + frontend)
	@echo "🔍 Checking service health..."
	@curl -f http://localhost:5000/ > /dev/null 2>&1 && echo "✅ Flask API: OK" || echo "❌ Flask API: DOWN"
	@curl -f http://localhost:3000/ > /dev/null 2>&1 && echo "✅ React App: OK" || echo "❌ React App: DOWN"
	@curl -f http://localhost:8081/ > /dev/null 2>&1 && echo "✅ Mongo Express: OK" || echo "❌ Mongo Express: DOWN"
	@docker compose exec mongodb mongosh --eval "db.adminCommand('ping')" interim_app > /dev/null 2>&1 && echo "✅ MongoDB: OK" || echo "❌ MongoDB: DOWN"

# Development helpers
install-deps: ## Install Python dependencies using pip
	cd backend && pip install -r requirements.txt -r requirements-test.txt

install-frontend-deps: ## Install frontend dependencies locally
	cd frontend && npm install

install-all-deps: ## Install all dependencies (backend + frontend)
	make install-deps
	make install-frontend-deps

# Code formatting and linting
format: ## Format backend code using Ruff
	docker compose exec backend ruff format .
	docker compose exec backend ruff check --fix .

format-local: ## Format backend code locally using Ruff
	cd backend && ruff format .
	cd backend && ruff check --fix .

format-frontend: ## Format frontend code
	docker compose exec frontend npm run format

format-all: ## Format all code (backend + frontend)
	make format
	make format-frontend

lint: ## Lint backend code using Ruff
	docker compose exec backend ruff check .

lint-local: ## Lint backend code locally using Ruff
	cd backend && ruff check .

lint-frontend: ## Lint frontend code
	docker compose exec frontend npm run lint

lint-all: ## Lint all code (backend + frontend)
	make lint
	make lint-frontend

# Dependency management
freeze-deps: ## Freeze current dependencies to requirements.txt
	cd backend && pip freeze > requirements-frozen.txt

update-deps: ## Update a specific package (usage: make update-deps PACKAGE=flask)
	cd backend && pip install --upgrade $(PACKAGE)
	@echo "Don't forget to update requirements.txt manually!"

add-dep: ## Add a new dependency (usage: make add-dep PACKAGE=requests)
	cd backend && pip install $(PACKAGE)
	@echo "Don't forget to add $(PACKAGE) to requirements.txt!"

# Frontend specific commands
frontend-build: ## Build frontend for production
	docker compose exec frontend npm run build

frontend-lint: ## Lint frontend code
	docker compose exec frontend npm run lint

frontend-dev: ## Start frontend in development mode (hot reload)
	docker compose exec frontend npm start

# Quick aliases
start: up ## Alias for 'up'
stop: down ## Alias for 'down'