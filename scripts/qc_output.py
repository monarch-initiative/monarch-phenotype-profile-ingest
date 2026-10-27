"""
Post-transform QC: fail the build when an output file does not look right.

Run after the transforms (`just qc`, part of `just run`, so the release workflow
fails instead of publishing a bad file). Each expectation names an output edge
file, a column, and the minimum fraction of rows whose value must start with a
given prefix. Row counts are checked downstream by monarch-ingest's qc_expect.yaml;
this catches silent content regressions that keep the row count intact, such as
the Mondo SSSOM header being mis-parsed so no disease id was mapped to MONDO.

Usage: python scripts/qc_output.py [OUTPUT_DIR]   (default: output/)
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PrefixExpectation:
    file: str
    column: str
    prefix: str
    min_fraction: float
    why: str


EXPECTATIONS: list[PrefixExpectation] = [
    PrefixExpectation(
        file="hpoa_gene_to_phenotype_edges.tsv",
        column="disease_context_qualifier",
        prefix="MONDO:",
        min_fraction=0.90,
        why="OMIM/ORPHA disease ids are mapped to MONDO through mondo_sssom_config.yaml; "
        "a low fraction means the SSSOM mapping was not applied (e.g. header mis-parsed).",
    ),
]


def check_prefix(output_dir: Path, expectation: PrefixExpectation) -> tuple[bool, str]:
    path = output_dir / expectation.file
    if not path.is_file():
        return False, f"{expectation.file}: file not found in {output_dir}"

    total = matching = 0
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if expectation.column not in (reader.fieldnames or []):
            return False, f"{expectation.file}: column {expectation.column!r} missing from header"
        for row in reader:
            total += 1
            if (row.get(expectation.column) or "").startswith(expectation.prefix):
                matching += 1

    if total == 0:
        return False, f"{expectation.file}: no data rows"

    fraction = matching / total
    summary = (
        f"{expectation.file}: {matching}/{total} ({fraction:.1%}) rows have "
        f"{expectation.column} starting with {expectation.prefix!r} (min {expectation.min_fraction:.0%})"
    )
    if fraction < expectation.min_fraction:
        return False, f"{summary}\n    {expectation.why}"
    return True, summary


def run(output_dir: Path) -> int:
    failures = 0
    for expectation in EXPECTATIONS:
        ok, message = check_prefix(output_dir, expectation)
        print(("PASS " if ok else "FAIL ") + message)
        failures += not ok
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output")))
