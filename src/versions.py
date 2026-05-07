"""Upstream source version fetcher for monarch-phenotype-profile-ingest.

Three top-level sources:
  - infores:hpoa  — HPO annotation files (phenotype.hpoa carries `#version:` header)
  - infores:hp    — the HP ontology .obo (HTTP Last-Modified)
  - infores:mondo — Mondo SSSOM mapping (HTTP Last-Modified)

Nested under infores:hpoa, one SourceVersion per contributing primary source
(OMIM, Orphanet, DECIPHER) — discovered from the `#description:` header line
of phenotype.hpoa. Edges in this ingest's output carry per-row
`primary_knowledge_source` (see src/phenotype_ingest_utils.py::get_knowledge_sources),
so a downstream consumer (e.g. monarch-app) can resolve an edge's exact
upstream version even though everything was retrieved via HPOA.

HPOA's header does not carry per-source dates — its bundle `#version:` is
the best as-of we have, so each nested entry uses that with
`version_method: hpoa_bundle` to make the audit trail explicit.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from kozahub_metadata_schema import (
    now_iso,
    urls_from_download_yaml,
    version_from_file_header,
    version_from_http_last_modified,
)


INGEST_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_YAML = INGEST_DIR / "download.yaml"
DATA_DIR = INGEST_DIR / "data"

# Tokens that may appear in phenotype.hpoa's `#description:` line, mapped to
# (infores, human-readable name). Matched case-insensitively.
HPOA_SUB_SOURCES = {
    "OMIM": ("infores:omim", "OMIM"),
    "ORPHANET": ("infores:orphanet", "Orphanet"),
    "DECIPHER": ("infores:decipher", "DECIPHER"),
}


def _hpoa_sub_sources(hpoa_file: Path, hpoa_url: str, hpoa_version: str, now: str) -> list[dict[str, Any]]:
    """Parse phenotype.hpoa #description: for contributing sources.

    Example header:
      #description: "HPO annotations for rare diseases [8576: OMIM; 47: DECIPHER; 4337 ORPHANET]"
    """
    if not hpoa_file.is_file():
        return []
    try:
        with hpoa_file.open() as f:
            description = ""
            for line in f:
                if not line.startswith("#"):
                    break
                if line.startswith("#description:"):
                    description = line
                    break
        if not description:
            return []
    except Exception:
        return []

    found: list[dict[str, Any]] = []
    for token, (infores, name) in HPOA_SUB_SOURCES.items():
        if re.search(rf"\b{token}\b", description, re.IGNORECASE):
            found.append({
                "id": infores,
                "name": name,
                "urls": [hpoa_url],
                "version": hpoa_version,
                "version_method": "hpoa_bundle",
                "retrieved_at": now,
            })
    return found


def get_source_versions() -> list[dict[str, Any]]:
    hpoa_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["obo/hp/hpoa"])
    hp_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["obo/hp.obo"])
    mondo_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["data.monarchinitiative.org/mappings"])
    now = now_iso()

    sources: list[dict[str, Any]] = []

    if hpoa_urls:
        hpoa_file = DATA_DIR / "phenotype.hpoa"
        if hpoa_file.is_file():
            ver, method = version_from_file_header(
                hpoa_file, pattern=r"#version:\s*(\S+)", comment_prefix="#"
            )
        else:
            ver, method = "unknown", "unavailable"
        entry: dict[str, Any] = {
            "id": "infores:hpoa",
            "name": "HPO Annotations (HPOA)",
            "urls": hpoa_urls,
            "version": ver,
            "version_method": method,
            "retrieved_at": now,
        }
        phenotype_hpoa_url = next((u for u in hpoa_urls if u.endswith("phenotype.hpoa")), hpoa_urls[0])
        nested = _hpoa_sub_sources(hpoa_file, phenotype_hpoa_url, ver, now)
        if nested:
            entry["sources"] = nested
        sources.append(entry)

    if hp_urls:
        ver, method = version_from_http_last_modified(hp_urls[0])
        sources.append({
            "id": "infores:hp",
            "name": "Human Phenotype Ontology (HP)",
            "urls": hp_urls,
            "version": ver,
            "version_method": method,
            "retrieved_at": now,
        })

    if mondo_urls:
        ver, method = version_from_http_last_modified(mondo_urls[0])
        sources.append({
            "id": "infores:mondo",
            "name": "Mondo Disease Ontology (SSSOM)",
            "urls": mondo_urls,
            "version": ver,
            "version_method": method,
            "retrieved_at": now,
        })

    return sources
