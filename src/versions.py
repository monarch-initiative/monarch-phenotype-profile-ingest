"""Upstream source version fetcher for monarch-phenotype-profile-ingest.

Three logical sources:
  - infores:hpoa  — HPO annotation files (phenotype.hpoa carries `#version:` header)
  - infores:hp    — the HP ontology .obo (HTTP Last-Modified)
  - infores:mondo — Mondo SSSOM mapping (HTTP Last-Modified)
"""

from __future__ import annotations

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
        sources.append({
            "id": "infores:hpoa",
            "name": "HPO Annotations (HPOA)",
            "urls": hpoa_urls,
            "version": ver,
            "version_method": method,
            "retrieved_at": now,
        })

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
