# monarch-phenotype-profile-ingest justfile

# Configuration
TRANSFORMS := "gene_to_phenotype disease_to_phenotype gene_to_disease disease_mode_of_inheritance"

# Default recipe
default:
    @just --list

# Install dependencies
[group('project management')]
install:
    uv sync --group dev

# Download data files
[group('ingest')]
download: install
    kghub-downloader download -y download.yaml

# Run preprocessing step
[group('ingest')]
preprocess:
    python scripts/gene_to_phenotype_extras.py

# Run all transforms
[group('ingest')]
transform-all: preprocess
    #!/usr/bin/env bash
    for t in {{TRANSFORMS}}; do
        echo "Running transform: $t"
        koza transform -s src/${t}_transform.yaml -o output/${t}
    done

# Run a single transform
[group('ingest')]
transform NAME:
    koza transform -s src/{{NAME}}_transform.yaml -o output/{{NAME}}

# Run full pipeline: download, preprocess, transform, test
[group('ingest')]
run: download transform-all test

# Run tests
[group('development')]
test: install
    pytest tests/

# Run tests with coverage
[group('development')]
test-cov: install
    pytest --cov=. --cov-report=term-missing

# Clean output files
[group('development')]
clean:
    rm -rf output/
    rm -f data/genes_to_phenotype_preprocessed.tsv
