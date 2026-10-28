"""
Upstream source version fetcher for monarch-phenotype-profile-ingest.

Five top-level sources:
  - infores:hpoa     — HPO annotation files (phenotype.hpoa carries `#version:` header)
  - infores:orphanet — Orphanet product 6 gene-disease associations, retrieved directly
                       (en_product6.xml carries a `<JDBOR date="...">` root attribute)
  - infores:hgnc     — HGNC complete set, used to resolve product 6 genes to NCBIGene (HTTP Last-Modified)
  - infores:hp       — the HP ontology .obo (HTTP Last-Modified)
  - infores:mondo    — Mondo SSSOM mapping (HTTP Last-Modified)

Nested under infores:hpoa, one SourceVersion per contributing primary source
(OMIM, Orphanet, DECIPHER) — discovered from the `#description:` header line
of phenotype.hpoa. Edges in this ingest's output carry per-row
`primary_knowledge_source` (see src/disease_to_phenotype_transform.py),
so a downstream consumer (e.g. monarch-app) can resolve an edge's exact
upstream version even though everything was retrieved via HPOA.

HPOA's header carries no per-source release dates, but the per-row
`biocuration` column has dates like `ORPHA:orphadata[2026-01-08]` or
`HPO:probinson[2024-03-14]`. The most recent biocuration date for rows
attributed to a given source is the best in-file signal we have for "as-of
when did HPOA last touch this source's content" — notably surfaces frozen
sources like DECIPHER (max date ~2013) that the bundle date would obscure.
We do not reach outside HPOA to upstream APIs.
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

# Tokens in phenotype.hpoa's `#description:` line, with the matching
# `database_id` row prefix and target (infores, name).
HPOA_SUB_SOURCES = {
    "OMIM":     {"row_prefix": "OMIM",     "infores": "infores:omim",     "name": "OMIM"},
    "ORPHANET": {"row_prefix": "ORPHA",    "infores": "infores:orphanet", "name": "Orphanet"},
    "DECIPHER": {"row_prefix": "DECIPHER", "infores": "infores:decipher", "name": "DECIPHER"},
}

_BIOCURATION_DATE = re.compile(r"\[(\d{4}-\d{2}-\d{2})\]")

# en_product6.xml root: <JDBOR date="2026-06-23 07:57:31" version="1.3.42 / 4.1.8 [2025-03-03]" ...>
_ORPHANET_JDBOR_DATE = r'<JDBOR[^>]*\bdate="(\d{4}-\d{2}-\d{2})'


def _orphanet_product6_version(xml_file: Path) -> tuple[str, str]:
    """
    Version Orphanet product 6 by the export date on its JDBOR root element.

    The XML prologue and root tag are the first two lines and both start with `<`,
    so the generic header scanner (which stops at the first non-prefixed line)
    reaches the root attribute before descending into the document body.
    """
    if not xml_file.is_file():
        return "unknown", "unavailable"
    return version_from_file_header(xml_file, pattern=_ORPHANET_JDBOR_DATE, comment_prefix="<")


def _scan_hpoa(hpoa_file: Path) -> tuple[str, dict[str, str]]:
    """
    Read phenotype.hpoa once. Return (description_line, {row_prefix: max_date}).

    `description_line` is the `#description:` header (used to discover which
    sub-sources are present). The dict maps `database_id` row prefix
    (OMIM/ORPHA/DECIPHER) to the latest biocuration date observed for rows
    of that source.
    """
    description = ""
    max_dates: dict[str, str] = {}
    with hpoa_file.open() as f:
        for line in f:
            if line.startswith("#"):
                if line.startswith("#description:") and not description:
                    description = line
                continue
            if line.startswith("database_id"):
                continue
            row_prefix = line.split(":", 1)[0]
            for m in _BIOCURATION_DATE.finditer(line):
                d = m.group(1)
                cur = max_dates.get(row_prefix)
                if cur is None or d > cur:
                    max_dates[row_prefix] = d
    return description, max_dates


def _hpoa_sub_sources(hpoa_file: Path, hpoa_url: str, hpoa_version: str, now: str) -> list[dict[str, Any]]:
    """
    Discover contributing sources from phenotype.hpoa and version each by
    its most recent biocuration date.

    Falls back to the HPOA bundle version (`hpoa_bundle`) for a discovered
    source whose rows yielded no parseable biocuration dates.
    """
    if not hpoa_file.is_file():
        return []
    try:
        description, max_dates = _scan_hpoa(hpoa_file)
    except Exception:
        return []
    if not description:
        return []

    found: list[dict[str, Any]] = []
    for token, meta in HPOA_SUB_SOURCES.items():
        if not re.search(rf"\b{token}\b", description, re.IGNORECASE):
            continue
        max_date = max_dates.get(meta["row_prefix"])
        if max_date:
            ver, method = max_date, "hpoa_biocuration_max"
        else:
            ver, method = hpoa_version, "hpoa_bundle"
        found.append({
            "id": meta["infores"],
            "name": meta["name"],
            "urls": [hpoa_url],
            "version": ver,
            "version_method": method,
            "retrieved_at": now,
        })
    return found


def get_source_versions() -> list[dict[str, Any]]:
    hpoa_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["obo/hp/hpoa"])
    hp_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["obo/hp.obo"])
    mondo_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["data.monarchinitiative.org/mappings"])
    orphanet_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["orphadata.com"])
    hgnc_urls = urls_from_download_yaml(DOWNLOAD_YAML, contains=["hgnc_complete_set"])
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

    if orphanet_urls:
        ver, method = _orphanet_product6_version(DATA_DIR / "en_product6.xml")
        sources.append({
            "id": "infores:orphanet",
            "name": "Orphanet (product 6: genes associated with rare diseases)",
            "urls": orphanet_urls,
            "version": ver,
            "version_method": method,
            "retrieved_at": now,
        })

    if hgnc_urls:
        ver, method = version_from_http_last_modified(hgnc_urls[0])
        sources.append({
            "id": "infores:hgnc",
            "name": "HGNC complete set",
            "urls": hgnc_urls,
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
