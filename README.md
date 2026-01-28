# monarch-phenotype-profile-ingest

Monarch KG ingest for phenotypes from Human Phenotype Ontology Annotations (HPOA).

## Overview

This ingest transforms HPOA data into Biolink Model-compliant knowledge graph edges. It produces 4 types of associations:

1. **Gene to Phenotype** - Associations between genes and phenotypic features
2. **Disease to Phenotype** - Associations between diseases and phenotypic features
3. **Gene to Disease** - Causal and correlated gene-disease associations
4. **Disease Mode of Inheritance** - Disease to genetic inheritance mode associations

## Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [just](https://github.com/casey/just) command runner

## Installation

```bash
# Using uv (recommended)
uv pip install -e ".[dev]"

# Or using just
just install
```

## Usage

This project uses a justfile for common tasks. To see available commands:

```bash
just --list
```

### Full Pipeline

```bash
# Download data, preprocess, and run all transforms
just run
```

### Step by Step

```bash
# Download source data
just download

# Run preprocessing (required for gene_to_phenotype)
just preprocess

# Run all transforms
just transform

# Or run a single transform
just transform-one disease_to_phenotype
```

### Testing

```bash
just test
```

## Project Structure

```
.
├── download.yaml          # Data download configuration
├── justfile               # Task runner commands
├── pyproject.toml         # Project configuration
├── src/                   # Transform code (flat structure)
│   ├── *_transform.py     # Python transform functions
│   ├── *_transform.yaml   # Koza configurations
│   └── phenotype_ingest_utils.py
├── scripts/               # Preprocessing scripts
│   └── gene_to_phenotype_extras.py
└── tests/                 # Test files
```

## Data Sources

- [HPOA genes_to_phenotype.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt)
- [HPOA genes_to_disease.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_disease.txt)
- [HPOA phenotype.hpoa](http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa)
- [Mondo SSSOM mappings](https://data.monarchinitiative.org/mappings/latest/mondo.sssom.tsv)
- [HP ontology](http://purl.obolibrary.org/obo/hp.obo)
