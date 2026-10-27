"""Tests for scripts/qc_output.py, the post-transform output check."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "qc_output.py"
spec = importlib.util.spec_from_file_location("qc_output", SCRIPT)
qc_output = importlib.util.module_from_spec(spec)
sys.modules["qc_output"] = qc_output
spec.loader.exec_module(qc_output)

HEADER = "id\tsubject\tpredicate\tobject\tdisease_context_qualifier\n"


def write_g2p(tmp_path: Path, contexts: list[str]) -> Path:
    out = tmp_path / "hpoa_gene_to_phenotype_edges.tsv"
    rows = (f"uuid:{i}\tNCBIGene:1\tbiolink:has_phenotype\tHP:1\t{c}\n" for i, c in enumerate(contexts))
    out.write_text(HEADER + "".join(rows))
    return tmp_path


def test_passes_when_mondo_fraction_is_high(tmp_path: Path):
    out = write_g2p(tmp_path, ["MONDO:1"] * 95 + ["OMIM:1"] * 5)
    assert qc_output.run(out) == 0


def test_fails_when_no_row_is_mondo_mapped(tmp_path: Path, capsys: pytest.CaptureFixture):
    out = write_g2p(tmp_path, ["OMIM:1"] * 50 + ["ORPHA:1"] * 50)
    assert qc_output.run(out) == 1
    assert "FAIL hpoa_gene_to_phenotype_edges.tsv: 0/100" in capsys.readouterr().out


def test_fails_when_file_missing(tmp_path: Path):
    assert qc_output.run(tmp_path) == 1


def test_fails_when_column_missing(tmp_path: Path):
    (tmp_path / "hpoa_gene_to_phenotype_edges.tsv").write_text("id\tsubject\nuuid:1\tNCBIGene:1\n")
    assert qc_output.run(tmp_path) == 1


def test_fails_when_empty(tmp_path: Path):
    (tmp_path / "hpoa_gene_to_phenotype_edges.tsv").write_text(HEADER)
    assert qc_output.run(tmp_path) == 1
