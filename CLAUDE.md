# CLAUDE.md

This file provides guidance for Claude Code when working with this repository.

## Project Overview

This is a Koza-based ingest that transforms Human Phenotype Ontology Annotation (HPOA) data, plus Orphanet product 6 gene-disease associations, into Biolink Model-compliant knowledge graph edges.

## Project Structure

- `download.yaml` - kghub-downloader configuration for fetching source data
- `src/` - Transform code and YAML configurations (flat structure)
  - `*_transform.py` - Python transform functions
  - `*_transform.yaml` - Koza transform configurations
  - `phenotype_ingest_utils.py` - Shared utility functions
  - `orphanet_gene_to_disease_utils.py` - Orphanet product 6 parsing and association-type mapping
  - `mondo_sssom_config.yaml` - SSSOM mapping configuration
  - `versions.py` - Per-ingest upstream version fetcher (consumed by `just metadata`)
- `scripts/` - Utility scripts
  - `orphanet_gene_to_disease_extras.py` - Flattens en_product6.xml to data/orphanet_gene_to_disease.tsv (genes resolved to NCBIGene via HGNC)
  - `gene_to_phenotype_extras.py` - DuckDB-based preprocessing (joins HPOA g2p with OMIM types from HPOA and Orphanet types from product 6)
  - `qc_output.py` - Post-transform output checks (g2p disease_context_qualifier must be MONDO-mapped, Orphanet g2d must be mostly causal); `just qc`, part of `just run`
  - `write_metadata.py` - Emits `output/release-metadata.yaml` from `versions.py`
- `tests/` - Pytest test files
- `output/` - Generated nodes and edges (gitignored)
  - `release-metadata.yaml` - Per-build manifest of upstream sources, versions, artifacts (kozahub-metadata-schema)
- `data/` - Downloaded source data (gitignored)

## Transforms

This ingest has 4 transforms:
1. `gene_to_phenotype` - Gene to phenotype associations (requires preprocessing)
2. `disease_to_phenotype` - Disease to phenotype associations
3. `orphanet_gene_to_disease` - Orphanet gene to disease associations from product 6 (requires preprocessing)
4. `disease_mode_of_inheritance` - Disease to mode of inheritance associations

OMIM gene-to-disease associations are not produced here (see omim-ingest). HPOA's genes_to_disease.txt is only
used for OMIM association types in the gene_to_phenotype preprocess; its Orphanet rows are all `UNKNOWN`, which
is why Orphanet g2d is read from product 6 directly (monarch-app#1488).

## Commands

Using the justfile:
- `just download` - Download source data
- `just preprocess` - Run preprocessing (creates orphanet_gene_to_disease.tsv, then genes_to_phenotype_preprocessed.tsv)
- `just transform` - Run all transforms (includes preprocessing)
- `just transform-one NAME` - Run a single transform
- `just qc` - Check output files against expectations in `scripts/qc_output.py` (fails the release workflow on regression)
- `just metadata` - Emit `output/release-metadata.yaml`
- `just test` - Run tests
- `just run` - Full pipeline

## Notes

- The gene_to_phenotype transform requires a preprocessing step that joins multiple data files using DuckDB
- Only g2p rows whose gene-disease association is MENDELIAN are emitted; for Orphanet diseases that means
  product 6 type "Disease-causing germline mutation(s) [...] in" with status Assessed
- The orphanet_gene_to_disease transform reads a flattened TSV; koza has no XML reader
- The disease_mode_of_inheritance transform loads hp.obo at module level to filter inheritance terms
- Tests use KozaTransform with PassthroughWriter for unit testing

## Release Metadata

Every kozahub ingest emits an `output/release-metadata.yaml` describing the upstream sources, their versions, the artifacts produced, and the versions of build-time tools. This file is the contract monarch-ingest reads to assemble the merged knowledge graph's release receipt.

`src/versions.py` is the only per-ingest piece — it implements `get_source_versions()` returning a list of SourceVersion dicts. The `kozahub_metadata_schema` package provides reusable fetchers for the common patterns (HTTP Last-Modified, GitHub releases, URL-path regex, file-header parsing). The boilerplate (transform-content hashing, tool versions, build_version composition, yaml emission) is handled by `scripts/write_metadata.py`.

The `kozahub-metadata-schema` repo is expected as a sibling checkout (path-dep). Switch to a git or PyPI dep once published.

## Skills

- `.claude/skills/update-template.md` - Update to latest template version
