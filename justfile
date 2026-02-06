# monarch-phenotype-profile-ingest justfile

# Package directory
PKG := "src"

# Explicitly enumerate transforms (add new ingests here)
TRANSFORMS := "gene_to_phenotype_transform disease_to_phenotype_transform gene_to_disease_transform disease_mode_of_inheritance_transform"

# List all commands
_default:
    @just --list

# Install dependencies
[group('project management')]
install:
    uv sync

# Download source data
[group('ingest')]
download: install
    uv run downloader download.yaml

# Run preprocessing step
[group('ingest')]
preprocess:
    uv run python scripts/gene_to_phenotype_extras.py

# Run all transforms
[group('ingest')]
transform-all: download preprocess
    #!/usr/bin/env bash
    set -euo pipefail
    for t in {{TRANSFORMS}}; do
        if [ -n "$t" ]; then
            echo "Transforming $t..."
            uv run koza transform {{PKG}}/$t.yaml
        fi
    done

# Run specific transform
[group('ingest')]
transform NAME:
    uv run koza transform {{PKG}}/{{NAME}}.yaml

# Run full pipeline: download, preprocess, transform, test
[group('ingest')]
run: transform-all test

# Run tests
[group('development')]
test: install
    uv run pytest

# Run tests with coverage
[group('development')]
test-cov: install
    uv run pytest --cov=. --cov-report=term-missing

# Clean output files
[group('ingest')]
clean:
    rm -rf output/
    rm -f data/genes_to_phenotype_preprocessed.tsv
