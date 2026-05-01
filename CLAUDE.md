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
  - `mondo_sssom_config.yaml` - SSSOM mapping configuration
  - `versions.py` - Per-ingest upstream version fetcher (consumed by `just metadata`)
- `scripts/` - Utility scripts
  - `gene_to_phenotype_extras.py` - DuckDB-based preprocessing
  - `write_metadata.py` - Emits `output/release-metadata.yaml` from `versions.py`
- `tests/` - Pytest test files
- `output/` - Generated nodes and edges (gitignored)
  - `release-metadata.yaml` - Per-build manifest of upstream sources, versions, artifacts (kozahub-metadata-schema)
- `data/` - Downloaded source data (gitignored)

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
- `just metadata` - Emit `output/release-metadata.yaml`
- `just test` - Run tests
- `just run` - Full pipeline

## Notes

- The gene_to_phenotype transform requires a preprocessing step that joins multiple data files using DuckDB
- The disease_mode_of_inheritance transform loads hp.obo at module level to filter inheritance terms
- Tests use KozaTransform with PassthroughWriter for unit testing

## Release Metadata

Every kozahub ingest emits an `output/release-metadata.yaml` describing the upstream sources, their versions, the artifacts produced, and the versions of build-time tools. This file is the contract monarch-ingest reads to assemble the merged knowledge graph's release receipt.

`src/versions.py` is the only per-ingest piece — it implements `get_source_versions()` returning a list of SourceVersion dicts. The `kozahub_metadata_schema` package provides reusable fetchers for the common patterns (HTTP Last-Modified, GitHub releases, URL-path regex, file-header parsing). The boilerplate (transform-content hashing, tool versions, build_version composition, yaml emission) is handled by `scripts/write_metadata.py`.

The `kozahub-metadata-schema` repo is expected as a sibling checkout (path-dep). Switch to a git or PyPI dep once published.

## Skills

- `.claude/skills/update-template.md` - Update to latest template version
