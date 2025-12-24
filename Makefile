# IPTV Aggregator - Makefile

.PHONY: help install demo demo-epg test lint format clean docker-build docker-run gh-demo gh-epg

help: ## Show this help
	@echo "IPTV Aggregator - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Done!"

install-dev: ## Install dev dependencies
	@echo "📦 Installing dev dependencies..."
	pip install -r requirements.txt
	pip install pytest pytest-asyncio ruff mypy
	@echo "✅ Done!"

demo: ## Run basic demo
	@echo "🚀 Running demo..."
	python demo.py
	@echo ""
	@echo "📁 Output:"
	@ls -lh output/

demo-epg: ## Run REAL EPG demo (scrapes BBC, ITV, etc)
	@echo "🌐 Running REAL EPG demo..."
	@echo "   This will scrape real TV schedules from BBC, ITV, Channel 4"
	@echo "   May take 1-2 minutes..."
	@echo ""
	python demo_real_epg.py
	@echo ""
	@echo "📊 EPG Stats:"
	@sqlite3 output/real_epg.db "SELECT COUNT(*) as programmes FROM programmes;"
	@sqlite3 output/real_epg.db "SELECT COUNT(DISTINCT channel_id) as channels FROM programmes;"

test: ## Run tests
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=src --cov-report=term

lint: ## Run linting
	@echo "🔍 Running linters..."
	ruff check src/
	ruff format --check src/
	mypy src/ --ignore-missing-imports

format: ## Format code
	@echo "✨ Formatting code..."
	ruff format src/
	ruff check --fix src/
	@echo "✅ Done!"

clean: ## Clean generated files
	@echo "🧹 Cleaning..."
	rm -rf output/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Done!"

db-inspect: ## Inspect SQLite database
	@echo "🔍 Database inspection:"
	@sqlite3 output/demo.db "SELECT COUNT(*) as channels FROM channels;"
	@sqlite3 output/demo.db "SELECT COUNT(*) as streams FROM streams;"
	@echo ""
	@echo "Sample channels:"
	@sqlite3 -header -column output/demo.db "SELECT id, name, country FROM channels LIMIT 10;"

epg-inspect: ## Inspect EPG database
	@echo "📺 EPG Database inspection:"
	@sqlite3 output/real_epg.db "SELECT COUNT(*) as total FROM programmes;"
	@sqlite3 output/real_epg.db "SELECT channel_id, COUNT(*) as count FROM programmes GROUP BY channel_id;"
	@echo ""
	@echo "Sample programmes:"
	@sqlite3 -header -column output/real_epg.db "SELECT channel_id, title, start FROM programmes LIMIT 10;"

playlist-preview: ## Preview M3U playlist
	@echo "📺 Playlist preview:"
	@head -30 output/demo.m3u

metadata-preview: ## Preview metadata JSON
	@echo "📊 Metadata preview:"
	@cat output/demo_metadata.json | python -m json.tool | head -50

# Docker commands
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t iptv-aggregator:latest .
	@echo "✅ Done!"

docker-run: ## Run in Docker
	@echo "🐳 Running in Docker..."
	docker run -v $(PWD)/output:/app/output iptv-aggregator:latest
	@echo ""
	@ls -lh output/

# GitHub Actions
gh-demo: ## Trigger demo workflow
	@echo "🚀 Triggering demo workflow..."
	gh workflow run demo.yml
	@echo "✅ Workflow dispatched!"
	@echo "🔎 Watch: gh run watch"

gh-epg: ## Trigger REAL EPG workflow
	@echo "🌐 Triggering REAL EPG workflow..."
	gh workflow run real-epg.yml
	@echo "✅ Workflow dispatched!"
	@echo "🔎 Watch: gh run watch"
	@echo ""
	@echo "This will scrape BBC, ITV, Channel 4 schedules"

gh-schedule: ## Trigger scheduled refresh
	@echo "🔄 Triggering scheduled refresh..."
	gh workflow run schedule.yml
	@echo "✅ Workflow dispatched!"

gh-logs: ## View latest workflow logs
	@echo "📜 Latest workflow logs:"
	gh run view --log

gh-artifacts: ## Download latest artifacts
	@echo "📦 Downloading artifacts..."
	gh run download
	@echo "✅ Done!"

# Development
dev-setup: install-dev ## Full dev setup
	@echo "🛠️  Setting up development environment..."
	pre-commit install 2>/dev/null || echo "pre-commit not available"
	@echo "✅ Dev environment ready!"

# Stats
stats: ## Show project stats
	@echo "📊 Project Statistics:"
	@echo ""
	@echo "Lines of code:"
	@find src/ -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Files:"
	@find src/ -name "*.py" | wc -l
	@echo ""
	@echo "Dependencies:"
	@grep -c "^[a-zA-Z]" requirements.txt

# Quick commands
q: demo ## Quick demo (alias)

qq: clean demo ## Clean + demo

qqq: clean install demo ## Full rebuild + demo

epg: demo-epg ## Quick EPG demo (alias)