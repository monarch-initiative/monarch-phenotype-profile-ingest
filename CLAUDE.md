# CLAUDE.md

This file provides guidance for Claude Code when working with this repository.

## Project Overview

This is a Koza-based ingest that transforms Human Phenotype Ontology Annotation (HPOA) data into Biolink Model-compliant knowledge graph edges.

## Project Structure

- `download.yaml` - kghub-downloader configuration for fetching source data
- `src/` - Transform code and YAML configurations (flat structure)
  - `*_transform.py` - Python transform functions
  - `*_transform.yaml` - Koza transform configurations
  - `phenotype_ingest_utils.py` - Shared utility functions
  - `monarch_constants.py` - Downloaded constants from monarch-ingest
  - `mondo_sssom_config.yaml` - SSSOM mapping configuration
- `scripts/` - Preprocessing scripts
  - `gene_to_phenotype_extras.py` - DuckDB-based preprocessing
- `tests/` - Pytest test files

## Transforms

This ingest has 4 transforms:
1. `gene_to_phenotype` - Gene to phenotype associations (requires preprocessing)
2. `disease_to_phenotype` - Disease to phenotype associations
3. `gene_to_disease` - Gene to disease associations
4. `disease_mode_of_inheritance` - Disease to mode of inheritance associations

## Commands

Using the justfile:
- `just download` - Download source data
- `just preprocess` - Run preprocessing (creates genes_to_phenotype_preprocessed.tsv)
- `just transform` - Run all transforms (includes preprocessing)
- `just transform-one NAME` - Run a single transform
- `just test` - Run tests
- `just run` - Full pipeline

## Notes

- The gene_to_phenotype transform requires a preprocessing step that joins multiple data files using DuckDB
- The disease_mode_of_inheritance transform loads hp.obo at module level to filter inheritance terms
- Tests use KozaTransform with PassthroughWriter for unit testing

## Skills

- `.claude/skills/update-template.md` - Update to latest template version
