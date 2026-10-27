"""
Regression test: infer the Mondo SSSOM header instead of hard-coding its line number.

mondo.sssom.tsv's `# curie_map:` comment block grows over time; when it passed the
hard-coded index the header was mis-parsed and no disease id was ever mapped to MONDO.
"""

from pathlib import Path

import yaml
from koza.io.reader.csv_reader import CSVReader
from koza.model.reader import CSVReaderConfig

CONFIG = Path(__file__).resolve().parents[1] / "src" / "mondo_sssom_config.yaml"


def sssom_fixture(comment_lines: int) -> str:
    header = "# curie_map:\n" + "".join(f"#   PFX{i}: http://example.org/{i}_\n" for i in range(comment_lines - 1))
    return (
        header
        + "subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\n"
        + "MONDO:0013588\tfoo\tskos:exactMatch\tOMIM:614129\tfoo\tsemapv:ManualMappingCuration\n"
        + "MONDO:0009341\tbar\tskos:exactMatch\tORPHA:110\tbar\tsemapv:ManualMappingCuration\n"
    )


def reader_config() -> CSVReaderConfig:
    reader = yaml.safe_load(CONFIG.read_text())["reader"]
    reader.pop("files")
    reader.pop("filters", None)
    reader.pop("format", None)
    return CSVReaderConfig(**reader)


def test_config_infers_header_regardless_of_comment_block_size(tmp_path: Path):
    config = reader_config()
    for comment_lines in (10, 52, 90):
        sssom = tmp_path / f"mondo_{comment_lines}.sssom.tsv"
        sssom.write_text(sssom_fixture(comment_lines))
        with sssom.open() as f:
            rows = list(CSVReader(f, config))
        assert [r["subject_id"] for r in rows] == ["MONDO:0013588", "MONDO:0009341"], comment_lines
        assert rows[0]["object_id"] == "OMIM:614129"
