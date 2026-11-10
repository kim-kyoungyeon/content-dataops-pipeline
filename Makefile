.PHONY: help build run test lint clean docker-build docker-run

# Default target
help:
	@echo "QA Data Pipeline - Available commands:"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code with black"
	@echo "  make clean       - Clean build artifacts"
	@echo ""
	@echo "  make run         - Run pipeline on bundled sample (override with INPUT=...)"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with Docker Compose"
	@echo "  make monitoring   - Start monitoring stack"
	@echo ""

INPUT ?= sample_data/sample_input.xlsx
OUTPUT_DIR ?= output

# Development
install:
	pip install -r requirements.txt

run:
	python main.py $(INPUT) --output-dir $(OUTPUT_DIR)

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	flake8 src/ tests/ --max-line-length=100
	mypy src/

format:
	black src/ tests/ main.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Docker
docker-build:
	docker build -t content-dataops-pipeline:latest .

docker-run:
	docker-compose up qa-pipeline

monitoring:
	docker-compose --profile monitoring up -d

monitoring-down:
	docker-compose --profile monitoring down
