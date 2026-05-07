"""Unit tests for src/versions.py — per-source nested SourceVersion emission.

Exercise the in-file parsing path (description discovery + biocuration
max-date scan) without hitting any network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src import versions


HPOA_FIXTURE = """\
#description: "HPO annotations for rare diseases [10: OMIM; 2: DECIPHER; 5 ORPHANET]"
#version: 2026-01-08
#tracker: https://github.com/obophenotype/human-phenotype-ontology/issues
#hpo-version: http://purl.obolibrary.org/obo/hp/releases/2026-01-08/hp.json
database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration
OMIM:619340\tFoo\t\tHP:0001\tPMID:1\tPCS\t\t\t\t\tP\tHPO:probinson[2024-03-14]
OMIM:619340\tFoo\t\tHP:0002\tPMID:1\tPCS\t\t\t\t\tP\tHPO:probinson[2021-06-21];HPO:lccarmody[2018-10-03]
OMIM:619341\tBar\t\tHP:0003\tPMID:2\tPCS\t\t\t\t\tP\tHPO:skoehler[2017-07-13]
ORPHA:33364\tBaz\t\tHP:0004\t\tIEA\t\t\t\t\tP\tORPHA:orphadata[2026-01-08]
ORPHA:33364\tBaz\t\tHP:0005\t\tIEA\t\t\t\t\tP\tORPHA:orphadata[2026-01-08]
DECIPHER:1\tQux\t\tHP:0006\t\tIEA\t\t\t\t\tP\tHPO:skoehler[2013-05-29]
DECIPHER:1\tQux\t\tHP:0007\t\tIEA\t\t\t\t\tP\tHPO:skoehler[2010-09-13]
"""


@pytest.fixture
def hpoa_file(tmp_path: Path) -> Path:
    p = tmp_path / "phenotype.hpoa"
    p.write_text(HPOA_FIXTURE)
    return p


def test_scan_hpoa_collects_max_date_per_source(hpoa_file: Path):
    description, max_dates = versions._scan_hpoa(hpoa_file)

    assert "[10: OMIM; 2: DECIPHER; 5 ORPHANET]" in description
    assert max_dates["OMIM"] == "2024-03-14"
    assert max_dates["DECIPHER"] == "2013-05-29"
    assert max_dates["ORPHA"] == "2026-01-08"


def test_hpoa_sub_sources_uses_biocuration_max_when_available(hpoa_file: Path):
    sources = versions._hpoa_sub_sources(
        hpoa_file, hpoa_url="http://x/phenotype.hpoa", hpoa_version="2026-01-08", now="2026-05-07T00:00:00Z"
    )

    by_id = {s["id"]: s for s in sources}
    assert by_id["infores:omim"]["version"] == "2024-03-14"
    assert by_id["infores:omim"]["version_method"] == "hpoa_biocuration_max"
    # DECIPHER is the load-bearing case: bundle says 2026, data is from 2013.
    assert by_id["infores:decipher"]["version"] == "2013-05-29"
    assert by_id["infores:decipher"]["version_method"] == "hpoa_biocuration_max"
    assert by_id["infores:orphanet"]["version"] == "2026-01-08"


def test_hpoa_sub_sources_falls_back_to_bundle_when_no_biocuration(tmp_path: Path):
    """A source declared in #description: but with no parseable biocuration
    dates should fall back to the HPOA bundle version."""
    p = tmp_path / "phenotype.hpoa"
    p.write_text(
        '#description: "HPO annotations [1: OMIM]"\n'
        "#version: 2026-01-08\n"
        "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration\n"
        "OMIM:1\tFoo\t\tHP:0001\t\tIEA\t\t\t\t\tP\t\n"  # empty biocuration
    )

    sources = versions._hpoa_sub_sources(p, hpoa_url="http://x", hpoa_version="2026-01-08", now="2026-05-07T00:00:00Z")

    assert len(sources) == 1
    assert sources[0]["id"] == "infores:omim"
    assert sources[0]["version"] == "2026-01-08"
    assert sources[0]["version_method"] == "hpoa_bundle"


def test_hpoa_sub_sources_skips_sources_absent_from_description(tmp_path: Path):
    """If a token isn't in #description:, don't emit an entry even if rows
    happen to be present (defensive — the canonical signal is the header)."""
    p = tmp_path / "phenotype.hpoa"
    p.write_text(
        '#description: "HPO annotations [10: OMIM]"\n'
        "#version: 2026-01-08\n"
        "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration\n"
        "OMIM:1\tFoo\t\tHP:0001\t\tIEA\t\t\t\t\tP\tHPO:x[2024-01-01]\n"
        "DECIPHER:1\tBar\t\tHP:0002\t\tIEA\t\t\t\t\tP\tHPO:x[2013-05-29]\n"
    )

    sources = versions._hpoa_sub_sources(p, hpoa_url="http://x", hpoa_version="2026-01-08", now="2026-05-07T00:00:00Z")

    ids = {s["id"] for s in sources}
    assert ids == {"infores:omim"}


def test_hpoa_sub_sources_returns_empty_when_no_description_header(tmp_path: Path):
    """No #description: header → no nesting (rather than misleading output)."""
    p = tmp_path / "phenotype.hpoa"
    p.write_text(
        "#version: 2026-01-08\n"
        "database_id\tdisease_name\n"
        "OMIM:1\tFoo\n"
    )

    sources = versions._hpoa_sub_sources(p, hpoa_url="http://x", hpoa_version="2026-01-08", now="2026-05-07T00:00:00Z")

    assert sources == []
