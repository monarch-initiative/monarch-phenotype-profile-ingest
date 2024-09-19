from pathlib import Path

from kgx.cli.cli_utils import transform as kgx_transform
from loguru import logger

logger.info(f"Creating rdf output: output/hpoa_generalized phenotype relationships.nt.gz ...")

#src_files = []
#src_nodes = f"output/hpoa_generalized phenotype relationships_nodes.tsv"
#src_edges = f"output/hpoa_generalized phenotype relationships_edges.tsv"

# Grab edge filepaths and generate a report for each one via duckdb
src_files = [str(fname) for fname in Path("./output").iterdir() 
             if str(fname).endswith("_edges.tsv")
             and fname.is_file()]

kgx_transform(inputs=src_files,
              input_format="tsv",
              stream=True,
              output=f"output/all_edges_kgx2rdf.nt.gz",
              output_format="nt",
              output_compression="gz")
