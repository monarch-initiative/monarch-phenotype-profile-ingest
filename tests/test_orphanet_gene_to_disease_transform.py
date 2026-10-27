"""
Tests for the direct Orphanet product 6 gene-to-disease ingest.

See https://github.com/monarch-initiative/monarch-app/issues/1488: every Orphanet row in
HPOA's genes_to_disease.txt is UNKNOWN, so the association type must come from product 6.
"""

from pathlib import Path

import pytest
from biolink_model.datamodel.pydanticmodel_v2 import (
    CausalGeneToDiseaseAssociation,
    CorrelatedGeneToDiseaseAssociation,
)
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from src.orphanet_gene_to_disease_transform import transform_record
from src.orphanet_gene_to_disease_utils import (
    ASSOCIATION_TYPE_MENDELIAN,
    ASSOCIATION_TYPE_POLYGENIC,
    ASSOCIATION_TYPE_SOMATIC,
    ASSOCIATION_TYPE_UNKNOWN,
    FORM_QUALIFIER_GAIN_OF_FUNCTION,
    FORM_QUALIFIER_LOSS_OF_FUNCTION,
    ORPHANET_BIOMARKER,
    ORPHANET_CANDIDATE_GENE,
    ORPHANET_DISEASE_CAUSING_GERMLINE,
    ORPHANET_DISEASE_CAUSING_GERMLINE_GOF,
    ORPHANET_DISEASE_CAUSING_GERMLINE_LOF,
    ORPHANET_DISEASE_CAUSING_SOMATIC,
    ORPHANET_FUSION_GENE,
    ORPHANET_MAJOR_SUSCEPTIBILITY_FACTOR,
    ORPHANET_MODIFYING_GERMLINE,
    ORPHANET_ROLE_IN_PHENOTYPE,
    ORPHANET_STATUS_ASSESSED,
    ORPHANET_STATUS_NOT_YET_ASSESSED,
    HgncGeneMap,
    get_orphanet_association_type_code,
    get_orphanet_form_qualifier,
    get_orphanet_predicate,
    parse_orphanet_product6,
    parse_source_of_validation,
    write_orphanet_gene_to_disease_tsv,
)
from src.phenotype_ingest_utils import (
    BIOLINK_CAUSES,
    BIOLINK_CONTRIBUTES_TO,
    BIOLINK_GENE_ASSOCIATED_WITH_CONDITION,
)

# --- association type / status -> type code -> predicate -------------------------------------

@pytest.mark.parametrize(
    ("association_type", "status", "expected_code"),
    [
        (ORPHANET_DISEASE_CAUSING_GERMLINE, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_MENDELIAN),
        (ORPHANET_DISEASE_CAUSING_GERMLINE_LOF, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_MENDELIAN),
        (ORPHANET_DISEASE_CAUSING_GERMLINE_GOF, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_MENDELIAN),
        (ORPHANET_DISEASE_CAUSING_SOMATIC, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_SOMATIC),
        (ORPHANET_MAJOR_SUSCEPTIBILITY_FACTOR, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_POLYGENIC),
        (ORPHANET_MODIFYING_GERMLINE, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_POLYGENIC),
        (ORPHANET_CANDIDATE_GENE, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        (ORPHANET_BIOMARKER, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        (ORPHANET_FUSION_GENE, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        (ORPHANET_ROLE_IN_PHENOTYPE, ORPHANET_STATUS_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        # Not yet assessed never yields a causal/contributing type, whatever the association type
        (ORPHANET_DISEASE_CAUSING_GERMLINE, ORPHANET_STATUS_NOT_YET_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        (ORPHANET_DISEASE_CAUSING_SOMATIC, ORPHANET_STATUS_NOT_YET_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        (ORPHANET_MAJOR_SUSCEPTIBILITY_FACTOR, ORPHANET_STATUS_NOT_YET_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
        (ORPHANET_CANDIDATE_GENE, ORPHANET_STATUS_NOT_YET_ASSESSED, ASSOCIATION_TYPE_UNKNOWN),
    ],
)
def test_association_type_code(association_type, status, expected_code):
    assert get_orphanet_association_type_code(association_type, status) == expected_code


def test_unknown_association_type_raises():
    with pytest.raises(ValueError):
        get_orphanet_association_type_code("Some new Orphanet category in", ORPHANET_STATUS_ASSESSED)


@pytest.mark.parametrize(
    ("code", "expected_predicate"),
    [
        (ASSOCIATION_TYPE_MENDELIAN, BIOLINK_CAUSES),
        (ASSOCIATION_TYPE_SOMATIC, BIOLINK_CAUSES),
        (ASSOCIATION_TYPE_POLYGENIC, BIOLINK_CONTRIBUTES_TO),
        (ASSOCIATION_TYPE_UNKNOWN, BIOLINK_GENE_ASSOCIATED_WITH_CONDITION),
    ],
)
def test_predicate(code, expected_predicate):
    assert get_orphanet_predicate(code) == expected_predicate


def test_unknown_code_raises():
    with pytest.raises(ValueError):
        get_orphanet_predicate("MAYBE")


@pytest.mark.parametrize(
    ("association_type", "expected"),
    [
        (ORPHANET_DISEASE_CAUSING_GERMLINE_LOF, FORM_QUALIFIER_LOSS_OF_FUNCTION),
        (ORPHANET_DISEASE_CAUSING_GERMLINE_GOF, FORM_QUALIFIER_GAIN_OF_FUNCTION),
        (ORPHANET_DISEASE_CAUSING_GERMLINE, None),
        (ORPHANET_DISEASE_CAUSING_SOMATIC, None),
    ],
)
def test_form_qualifier(association_type, expected):
    assert get_orphanet_form_qualifier(association_type) == expected


# --- SourceOfValidation -> PMIDs ------------------------------------------------------------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("22587682[PMID]", ["PMID:22587682"]),
        ("11309371[PMID]_15489334[PMID]", ["PMID:11309371", "PMID:15489334"]),
        ("27264419[PMID]_22482805[PMID", ["PMID:27264419", "PMID:22482805"]),
        ("27319779_27469900[PMID]", ["PMID:27319779", "PMID:27469900"]),
        ("29773874{PMID]", ["PMID:29773874"]),
        ("20301734PMID]", ["PMID:20301734"]),
        ("\xa023847139[PMID]", ["PMID:23847139"]),
        ("1[PMID]_1[PMID]", ["PMID:1"]),
        ("", []),
        (None, []),
    ],
)
def test_parse_source_of_validation(raw, expected):
    assert parse_source_of_validation(raw) == expected


# --- transform_record ------------------------------------------------------------------------

@pytest.fixture
def koza_transform():
    return KozaTransform(mappings={}, writer=PassthroughWriter(), extra_fields={})


@pytest.fixture
def row():
    return {
        "disease_id": "Orphanet:166024",
        "disease_name": "Multiple epiphyseal dysplasia-macrocephaly-facial dysmorphism syndrome",
        "disorder_type": "Disease",
        "gene_symbol": "KIF7",
        "gene_name": "kinesin family member 7",
        "gene_type": "gene with protein product",
        "hgnc_id": "HGNC:30497",
        "ncbi_gene_id": "NCBIGene:374654",
        "ensembl_gene_id": "ENSEMBL:ENSG00000166813",
        "omim_gene_id": "OMIM:611254",
        "association_type": ORPHANET_DISEASE_CAUSING_GERMLINE,
        "association_status": ORPHANET_STATUS_ASSESSED,
        "association_type_code": ASSOCIATION_TYPE_MENDELIAN,
        "publications": "PMID:22587682",
    }


def test_mendelian_row_is_causal(koza_transform, row):
    (association,) = transform_record(koza_transform, row)
    assert type(association) is CausalGeneToDiseaseAssociation
    assert association.subject == "NCBIGene:374654"
    assert association.predicate == BIOLINK_CAUSES
    assert association.object == "Orphanet:166024"
    assert association.original_subject == "HGNC:30497"
    assert association.original_predicate == ORPHANET_DISEASE_CAUSING_GERMLINE
    assert association.qualifiers == [ORPHANET_STATUS_ASSESSED]
    assert association.subject_form_or_variant_qualifier is None
    assert association.id.startswith("uuid:")
    assert association.publications == ["PMID:22587682"]
    assert association.primary_knowledge_source == "infores:orphanet"
    assert association.aggregator_knowledge_source == ["infores:monarchinitiative"]
    assert association.knowledge_level == "knowledge_assertion"
    assert association.agent_type == "manual_agent"


@pytest.mark.parametrize(
    ("association_type", "expected_qualifier"),
    [
        (ORPHANET_DISEASE_CAUSING_GERMLINE_LOF, FORM_QUALIFIER_LOSS_OF_FUNCTION),
        (ORPHANET_DISEASE_CAUSING_GERMLINE_GOF, FORM_QUALIFIER_GAIN_OF_FUNCTION),
    ],
)
def test_lof_gof_carry_form_qualifier(koza_transform, row, association_type, expected_qualifier):
    row = {**row, "association_type": association_type}
    (association,) = transform_record(koza_transform, row)
    assert type(association) is CausalGeneToDiseaseAssociation
    assert association.predicate == BIOLINK_CAUSES
    assert association.subject_form_or_variant_qualifier == expected_qualifier


def test_somatic_row_is_causal_with_original_predicate(koza_transform, row):
    row = {**row, "association_type": ORPHANET_DISEASE_CAUSING_SOMATIC}
    (association,) = transform_record(koza_transform, row)
    assert type(association) is CausalGeneToDiseaseAssociation
    assert association.predicate == BIOLINK_CAUSES
    assert association.original_predicate == ORPHANET_DISEASE_CAUSING_SOMATIC


@pytest.mark.parametrize(
    "association_type",
    [ORPHANET_MAJOR_SUSCEPTIBILITY_FACTOR, ORPHANET_MODIFYING_GERMLINE],
)
def test_susceptibility_and_modifier_contribute_to(koza_transform, row, association_type):
    (association,) = transform_record(koza_transform, {**row, "association_type": association_type})
    assert type(association) is CorrelatedGeneToDiseaseAssociation
    assert association.predicate == BIOLINK_CONTRIBUTES_TO


@pytest.mark.parametrize(
    "association_type",
    [ORPHANET_CANDIDATE_GENE, ORPHANET_BIOMARKER, ORPHANET_FUSION_GENE, ORPHANET_ROLE_IN_PHENOTYPE],
)
def test_non_causal_classes_never_cause(koza_transform, row, association_type):
    (association,) = transform_record(koza_transform, {**row, "association_type": association_type})
    assert type(association) is CorrelatedGeneToDiseaseAssociation
    assert association.predicate == BIOLINK_GENE_ASSOCIATED_WITH_CONDITION
    assert association.original_predicate == association_type


def test_not_yet_assessed_germline_is_not_causal(koza_transform, row):
    (association,) = transform_record(
        koza_transform, {**row, "association_status": ORPHANET_STATUS_NOT_YET_ASSESSED}
    )
    assert type(association) is CorrelatedGeneToDiseaseAssociation
    assert association.predicate == BIOLINK_GENE_ASSOCIATED_WITH_CONDITION
    assert association.qualifiers == [ORPHANET_STATUS_NOT_YET_ASSESSED]


def test_row_without_ncbi_gene_is_skipped(koza_transform, row):
    assert transform_record(koza_transform, {**row, "ncbi_gene_id": "", "hgnc_id": "HGNC:32944"}) == []


def test_empty_publications(koza_transform, row):
    (association,) = transform_record(koza_transform, {**row, "publications": ""})
    assert association.publications == []


# --- product 6 XML flattening ---------------------------------------------------------------

PRODUCT6_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<JDBOR date="2026-06-23 07:57:31" version="1.3.42 / 4.1.8 [2025-03-03]" copyright="Orphanet (c) 2026">
  <DisorderList count="2">
    <Disorder id="17601">
      <OrphaCode>166024</OrphaCode>
      <Name lang="en">Multiple epiphyseal dysplasia-macrocephaly-facial dysmorphism syndrome</Name>
      <DisorderType id="21394"><Name lang="en">Disease</Name></DisorderType>
      <DisorderGeneAssociationList count="2">
        <DisorderGeneAssociation>
          <SourceOfValidation>22587682[PMID]_11111111[PMID]</SourceOfValidation>
          <Gene id="20160">
            <Name lang="en">kinesin family member 7</Name>
            <Symbol>KIF7</Symbol>
            <GeneType id="25993"><Name lang="en">gene with protein product</Name></GeneType>
            <ExternalReferenceList count="3">
              <ExternalReference id="1">
                <Source>Ensembl</Source><Reference>ENSG00000166813</Reference>
              </ExternalReference>
              <ExternalReference id="2">
                <Source>HGNC</Source><Reference>30497</Reference>
              </ExternalReference>
              <ExternalReference id="3">
                <Source>OMIM</Source><Reference>611254</Reference>
              </ExternalReference>
            </ExternalReferenceList>
          </Gene>
          <DisorderGeneAssociationType id="25972">
            <Name lang="en">Disease-causing germline mutation(s) (loss of function) in</Name>
          </DisorderGeneAssociationType>
          <DisorderGeneAssociationStatus id="17991"><Name lang="en">Assessed</Name></DisorderGeneAssociationStatus>
        </DisorderGeneAssociation>
        <DisorderGeneAssociation>
          <SourceOfValidation/>
          <Gene id="99">
            <Name lang="en">spastic paraplegia 34</Name>
            <Symbol>SPG34</Symbol>
            <GeneType id="1"><Name lang="en">Disorder-associated locus</Name></GeneType>
            <ExternalReferenceList count="1">
              <ExternalReference id="4">
                <Source>HGNC</Source><Reference>32944</Reference>
              </ExternalReference>
            </ExternalReferenceList>
          </Gene>
          <DisorderGeneAssociationType id="18273">
            <Name lang="en">Candidate gene tested in</Name>
          </DisorderGeneAssociationType>
          <DisorderGeneAssociationStatus id="17992">
            <Name lang="en">Not yet assessed</Name>
          </DisorderGeneAssociationStatus>
        </DisorderGeneAssociation>
      </DisorderGeneAssociationList>
    </Disorder>
    <Disorder id="5">
      <OrphaCode>730300</OrphaCode>
      <Name lang="en">Some disorder</Name>
      <DisorderType id="21394"><Name lang="en">Malformation syndrome</Name></DisorderType>
      <DisorderGeneAssociationList count="1">
        <DisorderGeneAssociation>
          <SourceOfValidation>1[PMID]</SourceOfValidation>
          <Gene id="7">
            <Name lang="en">farnesyl-diphosphate farnesyltransferase 1</Name>
            <Symbol>FDFT1</Symbol>
            <GeneType id="25993"><Name lang="en">gene with protein product</Name></GeneType>
            <ExternalReferenceList count="0"/>
          </Gene>
          <DisorderGeneAssociationType id="17949">
            <Name lang="en">Disease-causing germline mutation(s) in</Name>
          </DisorderGeneAssociationType>
          <DisorderGeneAssociationStatus id="17991"><Name lang="en">Assessed</Name></DisorderGeneAssociationStatus>
        </DisorderGeneAssociation>
      </DisorderGeneAssociationList>
    </Disorder>
  </DisorderList>
</JDBOR>
"""

HGNC_FIXTURE = (
    "hgnc_id\tsymbol\tname\tlocus_group\tentrez_id\tensembl_gene_id\n"
    "HGNC:30497\tKIF7\tkinesin family member 7\tprotein-coding gene\t374654\tENSG00000166813\n"
    "HGNC:3629\tFDFT1\tfarnesyl-diphosphate farnesyltransferase 1\tprotein-coding gene\t2222\tENSG00000079459\n"
    "HGNC:99999\tNOENTREZ\tno entrez id\tother\t\t\n"
)


@pytest.fixture
def product6_files(tmp_path: Path):
    xml = tmp_path / "en_product6.xml"
    xml.write_text(PRODUCT6_FIXTURE)
    hgnc = tmp_path / "hgnc_complete_set.txt"
    hgnc.write_text(HGNC_FIXTURE)
    return xml, hgnc


def test_hgnc_gene_map(product6_files):
    _, hgnc = product6_files
    gene_map = HgncGeneMap(hgnc)
    assert gene_map.lookup("HGNC:30497", "KIF7") == "NCBIGene:374654"
    # symbol fallback when the HGNC reference is missing
    assert gene_map.lookup("", "FDFT1") == "NCBIGene:2222"
    # withdrawn HGNC id, unknown symbol
    assert gene_map.lookup("HGNC:32944", "SPG34") is None
    # entry without an entrez id is not mapped
    assert gene_map.lookup("HGNC:99999", "NOENTREZ") is None


def test_parse_product6(product6_files):
    xml, hgnc = product6_files
    rows = list(parse_orphanet_product6(xml, HgncGeneMap(hgnc)))
    assert len(rows) == 3

    kif7, spg34, fdft1 = rows
    assert kif7["disease_id"] == "Orphanet:166024"
    assert kif7["disease_name"].startswith("Multiple epiphyseal dysplasia")
    assert kif7["disorder_type"] == "Disease"
    assert kif7["gene_symbol"] == "KIF7"
    assert kif7["hgnc_id"] == "HGNC:30497"
    assert kif7["ncbi_gene_id"] == "NCBIGene:374654"
    assert kif7["ensembl_gene_id"] == "ENSEMBL:ENSG00000166813"
    assert kif7["omim_gene_id"] == "OMIM:611254"
    assert kif7["association_type"] == ORPHANET_DISEASE_CAUSING_GERMLINE_LOF
    assert kif7["association_status"] == ORPHANET_STATUS_ASSESSED
    assert kif7["association_type_code"] == ASSOCIATION_TYPE_MENDELIAN
    assert kif7["publications"] == "PMID:22587682;PMID:11111111"

    assert spg34["hgnc_id"] == "HGNC:32944"
    assert spg34["ncbi_gene_id"] == ""
    assert spg34["gene_type"] == "Disorder-associated locus"
    assert spg34["association_type_code"] == ASSOCIATION_TYPE_UNKNOWN
    assert spg34["publications"] == ""

    assert fdft1["disease_id"] == "Orphanet:730300"
    assert fdft1["hgnc_id"] == ""
    assert fdft1["ncbi_gene_id"] == "NCBIGene:2222"
    assert fdft1["association_type_code"] == ASSOCIATION_TYPE_MENDELIAN


def test_write_tsv_and_transform_round_trip(product6_files, tmp_path: Path, koza_transform):
    import csv

    xml, hgnc = product6_files
    out = tmp_path / "orphanet_gene_to_disease.tsv"
    counts = write_orphanet_gene_to_disease_tsv(xml, hgnc, out)
    assert counts == {"rows": 3, "unmapped_gene": 1}

    with open(out) as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    associations = [a for r in rows for a in transform_record(koza_transform, r)]
    assert [a.predicate for a in associations] == [BIOLINK_CAUSES, BIOLINK_CAUSES]
    assert associations[0].subject_form_or_variant_qualifier == FORM_QUALIFIER_LOSS_OF_FUNCTION
    assert associations[0].publications == ["PMID:22587682", "PMID:11111111"]
