"""
Orphanet product 6 (genes associated with rare diseases) processing utilities.

Product 6 (`en_product6.xml`, CC BY 4.0) carries a per-gene
`DisorderGeneAssociationType` and `DisorderGeneAssociationStatus` that HPOA's
genes_to_disease.txt collapses to `UNKNOWN` for every Orphanet row. Reading the
source directly lets Orphanet gene-to-disease associations be typed as causal
(and therefore feed gene-to-phenotype inference) the same way OMIM MENDELIAN
rows do.

See https://github.com/monarch-initiative/monarch-app/issues/1488
"""

from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from src.phenotype_ingest_utils import (
    BIOLINK_CAUSES,
    BIOLINK_CONTRIBUTES_TO,
    BIOLINK_GENE_ASSOCIATED_WITH_CONDITION,
)

# DisorderGeneAssociationType labels as they appear in en_product6.xml
ORPHANET_DISEASE_CAUSING_GERMLINE = "Disease-causing germline mutation(s) in"
ORPHANET_DISEASE_CAUSING_GERMLINE_LOF = "Disease-causing germline mutation(s) (loss of function) in"
ORPHANET_DISEASE_CAUSING_GERMLINE_GOF = "Disease-causing germline mutation(s) (gain of function) in"
ORPHANET_DISEASE_CAUSING_SOMATIC = "Disease-causing somatic mutation(s) in"
ORPHANET_MAJOR_SUSCEPTIBILITY_FACTOR = "Major susceptibility factor in"
ORPHANET_MODIFYING_GERMLINE = "Modifying germline mutation in"
ORPHANET_CANDIDATE_GENE = "Candidate gene tested in"
ORPHANET_BIOMARKER = "Biomarker tested in"
ORPHANET_FUSION_GENE = "Part of a fusion gene in"
ORPHANET_ROLE_IN_PHENOTYPE = "Role in the phenotype of"

# DisorderGeneAssociationStatus labels
ORPHANET_STATUS_ASSESSED = "Assessed"
ORPHANET_STATUS_NOT_YET_ASSESSED = "Not yet assessed"

# HPOA-style association type codes. MENDELIAN is the only code that feeds
# gene-to-phenotype inference (see scripts/gene_to_phenotype_extras.py and
# src/gene_to_phenotype_transform.yaml). SOMATIC is kept distinct so that a
# disease-causing somatic association can be asserted as causal in the KG
# without being treated as a germline/Mendelian gene-disease relationship.
ASSOCIATION_TYPE_MENDELIAN = "MENDELIAN"
ASSOCIATION_TYPE_SOMATIC = "SOMATIC"
ASSOCIATION_TYPE_POLYGENIC = "POLYGENIC"
ASSOCIATION_TYPE_UNKNOWN = "UNKNOWN"

_GERMLINE_CAUSAL_TYPES = {
    ORPHANET_DISEASE_CAUSING_GERMLINE,
    ORPHANET_DISEASE_CAUSING_GERMLINE_LOF,
    ORPHANET_DISEASE_CAUSING_GERMLINE_GOF,
}
_POLYGENIC_TYPES = {
    ORPHANET_MAJOR_SUSCEPTIBILITY_FACTOR,
    ORPHANET_MODIFYING_GERMLINE,
}
_NON_CAUSAL_TYPES = {
    ORPHANET_CANDIDATE_GENE,
    ORPHANET_BIOMARKER,
    ORPHANET_FUSION_GENE,
    ORPHANET_ROLE_IN_PHENOTYPE,
}
KNOWN_ASSOCIATION_TYPES = (
    _GERMLINE_CAUSAL_TYPES | {ORPHANET_DISEASE_CAUSING_SOMATIC} | _POLYGENIC_TYPES | _NON_CAUSAL_TYPES
)

# Biolink ChemicalOrGeneOrGeneProductFormOrVariantEnum values
FORM_QUALIFIER_LOSS_OF_FUNCTION = "loss_of_function_variant_form"
FORM_QUALIFIER_GAIN_OF_FUNCTION = "gain_of_function_variant_form"

ORPHANET_TYPE_TO_FORM_QUALIFIER: Dict[str, str] = {
    ORPHANET_DISEASE_CAUSING_GERMLINE_LOF: FORM_QUALIFIER_LOSS_OF_FUNCTION,
    ORPHANET_DISEASE_CAUSING_GERMLINE_GOF: FORM_QUALIFIER_GAIN_OF_FUNCTION,
}

ASSOCIATION_TYPE_CODE_TO_PREDICATE: Dict[str, str] = {
    ASSOCIATION_TYPE_MENDELIAN: BIOLINK_CAUSES,
    ASSOCIATION_TYPE_SOMATIC: BIOLINK_CAUSES,
    ASSOCIATION_TYPE_POLYGENIC: BIOLINK_CONTRIBUTES_TO,
    ASSOCIATION_TYPE_UNKNOWN: BIOLINK_GENE_ASSOCIATED_WITH_CONDITION,
}

ORPHANET_G2D_COLUMNS: List[str] = [
    "disease_id",
    "disease_name",
    "disorder_type",
    "gene_symbol",
    "gene_name",
    "gene_type",
    "hgnc_id",
    "ncbi_gene_id",
    "ensembl_gene_id",
    "omim_gene_id",
    "association_type",
    "association_status",
    "association_type_code",
    "publications",
]


def get_orphanet_association_type_code(association_type: str, association_status: str) -> str:
    """
    Collapse an Orphanet (DisorderGeneAssociationType, DisorderGeneAssociationStatus) pair to a type code.

    - MENDELIAN: any of the three "Disease-causing germline mutation(s)" types, status Assessed
    - SOMATIC:   "Disease-causing somatic mutation(s) in", status Assessed
    - POLYGENIC: "Major susceptibility factor in" / "Modifying germline mutation in", status Assessed
    - UNKNOWN:   candidate / biomarker / fusion / role-in-phenotype, or any type that is Not yet assessed

    Raises ValueError for an association type not in the known Orphanet vocabulary, so that
    a new upstream category is reviewed rather than silently mapped.
    """
    association_type = association_type.strip()
    if association_type not in KNOWN_ASSOCIATION_TYPES:
        raise ValueError(f"Unknown Orphanet DisorderGeneAssociationType: {association_type!r}")

    if association_status.strip() != ORPHANET_STATUS_ASSESSED:
        return ASSOCIATION_TYPE_UNKNOWN
    if association_type in _GERMLINE_CAUSAL_TYPES:
        return ASSOCIATION_TYPE_MENDELIAN
    if association_type == ORPHANET_DISEASE_CAUSING_SOMATIC:
        return ASSOCIATION_TYPE_SOMATIC
    if association_type in _POLYGENIC_TYPES:
        return ASSOCIATION_TYPE_POLYGENIC
    return ASSOCIATION_TYPE_UNKNOWN


def get_orphanet_predicate(association_type_code: str) -> str:
    """Map an association type code (from get_orphanet_association_type_code) to a Biolink predicate."""
    try:
        return ASSOCIATION_TYPE_CODE_TO_PREDICATE[association_type_code]
    except KeyError:
        raise ValueError(f"Unknown association type code: {association_type_code!r}") from None


def get_orphanet_form_qualifier(association_type: str) -> Optional[str]:
    """Return the Biolink subject_form_or_variant_qualifier for loss/gain-of-function types, else None."""
    return ORPHANET_TYPE_TO_FORM_QUALIFIER.get(association_type.strip())


_DIGITS = re.compile(r"\d+")


def parse_source_of_validation(source_of_validation: Optional[str]) -> List[str]:
    """
    Parse Orphanet's SourceOfValidation into a list of PMID CURIEs.

    The nominal format is `12345[PMID]_67890[PMID]`, but the field has typos in the wild
    (`12345{PMID]`, `12345PMID]`, `12345_67890[PMID]`, non-breaking spaces). Every run of
    digits is a PubMed id; nothing else has been observed in the field.
    """
    if not source_of_validation:
        return []
    pmids: List[str] = []
    for pmid in _DIGITS.findall(source_of_validation):
        curie = f"PMID:{pmid}"
        if curie not in pmids:
            pmids.append(curie)
    return pmids


class HgncGeneMap:
    """
    HGNC id / symbol -> NCBIGene id lookup built from hgnc_complete_set.txt.

    Product 6 identifies genes by HGNC id (and symbol) but never by NCBI Gene id, while
    the rest of this ingest (and HPOA) uses NCBIGene subjects. HGNC ids that are no longer
    in the complete set (withdrawn locus-type entries such as SPG34, SNORD116@) have no
    NCBIGene id and are left unmapped.
    """

    def __init__(self, hgnc_complete_set: Path):
        """Index hgnc_complete_set.txt by hgnc_id and by current symbol."""
        self.by_hgnc_id: Dict[str, str] = {}
        self.by_symbol: Dict[str, str] = {}
        with open(hgnc_complete_set, newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                entrez = (row.get("entrez_id") or "").strip()
                if not entrez:
                    continue
                ncbi_gene_id = f"NCBIGene:{entrez}"
                self.by_hgnc_id[row["hgnc_id"].strip()] = ncbi_gene_id
                symbol = (row.get("symbol") or "").strip()
                if symbol:
                    self.by_symbol[symbol] = ncbi_gene_id

    def lookup(self, hgnc_id: Optional[str], symbol: Optional[str]) -> Optional[str]:
        if hgnc_id and hgnc_id in self.by_hgnc_id:
            return self.by_hgnc_id[hgnc_id]
        if symbol and symbol in self.by_symbol:
            return self.by_symbol[symbol]
        return None


def _text(element: Optional[ET.Element], path: str) -> str:
    if element is None:
        return ""
    return (element.findtext(path) or "").strip()


def parse_orphanet_product6(xml_path: Path, gene_map: HgncGeneMap) -> Iterator[Dict[str, str]]:
    """
    Stream en_product6.xml and yield one flat row per DisorderGeneAssociation.

    Columns are ORPHANET_G2D_COLUMNS. `ncbi_gene_id` is empty when the gene could not be
    resolved through HGNC; `publications` is `;`-joined PMID CURIEs.
    """
    # Product 6 is a trusted download from Orphadata, parsed with the stdlib rather than defusedxml.
    for _, disorder in ET.iterparse(str(xml_path)):  # noqa: S314
        if disorder.tag != "Disorder":
            continue
        disease_id = f"Orphanet:{_text(disorder, 'OrphaCode')}"
        disease_name = _text(disorder, "Name")
        disorder_type = _text(disorder.find("DisorderType"), "Name")

        for association in disorder.iter("DisorderGeneAssociation"):
            gene = association.find("Gene")
            refs = {
                _text(ref, "Source"): _text(ref, "Reference")
                for ref in gene.iter("ExternalReference")
            } if gene is not None else {}
            hgnc_id = f"HGNC:{refs['HGNC']}" if refs.get("HGNC") else ""
            symbol = _text(gene, "Symbol")
            association_type = _text(association.find("DisorderGeneAssociationType"), "Name")
            association_status = _text(association.find("DisorderGeneAssociationStatus"), "Name")

            yield {
                "disease_id": disease_id,
                "disease_name": disease_name,
                "disorder_type": disorder_type,
                "gene_symbol": symbol,
                "gene_name": _text(gene, "Name"),
                "gene_type": _text(gene.find("GeneType") if gene is not None else None, "Name"),
                "hgnc_id": hgnc_id,
                "ncbi_gene_id": gene_map.lookup(hgnc_id, symbol) or "",
                "ensembl_gene_id": f"ENSEMBL:{refs['Ensembl']}" if refs.get("Ensembl") else "",
                "omim_gene_id": f"OMIM:{refs['OMIM']}" if refs.get("OMIM") else "",
                "association_type": association_type,
                "association_status": association_status,
                "association_type_code": get_orphanet_association_type_code(association_type, association_status),
                "publications": ";".join(parse_source_of_validation(_text(association, "SourceOfValidation"))),
            }
        disorder.clear()


def write_orphanet_gene_to_disease_tsv(xml_path: Path, hgnc_complete_set: Path, output_path: Path) -> Dict[str, int]:
    """Flatten product 6 to a TSV for the koza transform and the g2p preprocess join. Returns row counts."""
    gene_map = HgncGeneMap(hgnc_complete_set)
    counts = {"rows": 0, "unmapped_gene": 0}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ORPHANET_G2D_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in parse_orphanet_product6(xml_path, gene_map):
            counts["rows"] += 1
            if not row["ncbi_gene_id"]:
                counts["unmapped_gene"] += 1
            writer.writerow(row)
    return counts
