"""
Flatten Orphanet product 6 (en_product6.xml) into data/orphanet_gene_to_disease.tsv.

Genes are resolved to NCBIGene ids through hgnc_complete_set.txt. Run from the
ingest root (paths are relative), before scripts/gene_to_phenotype_extras.py,
which joins the resulting association_type_code into the g2p preprocess.
"""

from pathlib import Path

from loguru import logger

from src.orphanet_gene_to_disease_utils import write_orphanet_gene_to_disease_tsv

DATA_DIR = Path("data")

if __name__ == "__main__":
    counts = write_orphanet_gene_to_disease_tsv(
        xml_path=DATA_DIR / "en_product6.xml",
        hgnc_complete_set=DATA_DIR / "hgnc_complete_set.txt",
        output_path=DATA_DIR / "orphanet_gene_to_disease.tsv",
    )
    logger.info(
        f"Wrote {counts['rows']} Orphanet gene-disease associations "
        f"({counts['unmapped_gene']} without an NCBIGene id) to {DATA_DIR / 'orphanet_gene_to_disease.tsv'}"
    )
