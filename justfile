# monarch-phenotype-profile-ingest justfile

# Configuration
TRANSFORMS := "gene_to_phenotype disease_to_phenotype gene_to_disease disease_mode_of_inheritance"

# Default recipe
default:
    @just --list

# Download data files
download:
    kghub-downloader download -y download.yaml

# Run preprocessing step
preprocess:
    python scripts/gene_to_phenotype_extras.py

# Run all transforms
transform: preprocess
    #!/usr/bin/env bash
    for t in {{TRANSFORMS}}; do
        echo "Running transform: $t"
        koza transform -s src/${t}_transform.yaml -o output/${t}
    done

# Run a single transform
transform-one NAME:
    koza transform -s src/{{NAME}}_transform.yaml -o output/{{NAME}}

# Run tests
test:
    pytest tests/

# Full pipeline: download, preprocess, transform
run: download transform

# Clean output files
clean:
    rm -rf output/
    rm -f data/genes_to_phenotype_preprocessed.tsv

# Install dependencies
install:
    uv pip install -e ".[dev]"
