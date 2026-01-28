import pytest

from typing import List
from biolink_model.datamodel.pydanticmodel_v2 import CausalGeneToDiseaseAssociation
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from phenotype_ingest_utils import get_knowledge_sources, get_predicate
from monarch_constants import (
    BIOLINK_CAUSES,
    BIOLINK_CONTRIBUTES_TO,
    BIOLINK_GENE_ASSOCIATED_WITH_CONDITION,
    INFORES_MEDGEN,
    INFORES_MONARCHINITIATIVE,
    INFORES_OMIM,
    INFORES_ORPHANET
)
from gene_to_disease_transform import transform_record


@pytest.mark.parametrize(
    ("original_source", "expected_primary_knowledge_source", "expected_aggregator_knowledge_source"),
    [
        (
            "ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen",
            INFORES_OMIM,
            [INFORES_MEDGEN, INFORES_MONARCHINITIATIVE],
        ),
        ("http://www.orphadata.org/data/xml/en_product6.xml", INFORES_ORPHANET, [INFORES_MONARCHINITIATIVE]),
    ],
)
def test_knowledge_source(
    original_source: str, expected_primary_knowledge_source: str, expected_aggregator_knowledge_source: List[str]
):
    primary_knowledge_source, aggregator_knowledge_source = get_knowledge_sources(
        original_source, INFORES_MONARCHINITIATIVE
    )

    assert primary_knowledge_source == expected_primary_knowledge_source
    assert aggregator_knowledge_source.sort() == expected_aggregator_knowledge_source.sort()


@pytest.mark.parametrize(
    ("association", "expected_predicate"),
    [
        ("MENDELIAN", BIOLINK_CAUSES),
        ("POLYGENIC", BIOLINK_CONTRIBUTES_TO),
        ("UNKNOWN", BIOLINK_GENE_ASSOCIATED_WITH_CONDITION),
    ],
)
def test_predicate(association: str, expected_predicate: str):
    predicate = get_predicate(association)

    assert predicate == expected_predicate


@pytest.fixture
def row():
    return {
        'association_type': 'MENDELIAN',
        'disease_id': 'OMIM:212050',
        'gene_symbol': 'CARD9',
        'ncbi_gene_id': 'NCBIGene:64170',
        'source': 'ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen',
    }


@pytest.fixture
def basic_g2d_entities(row):
    koza_transform = KozaTransform(
        mappings={},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, row)


def test_hpoa_gene_to_disease(basic_g2d_entities):
    assert len(basic_g2d_entities) == 1
    association = basic_g2d_entities[0]
    assert isinstance(association, CausalGeneToDiseaseAssociation)
    assert association.subject == "NCBIGene:64170"
    assert association.object == "OMIM:212050"
    assert association.predicate == "biolink:causes"
    assert association.primary_knowledge_source == "infores:omim"
    assert association.aggregator_knowledge_source.sort() == ["infores:medgen", "infores:monarchinitiative"].sort()
