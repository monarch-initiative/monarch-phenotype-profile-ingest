import os
import sys
import pytest

from typing import List
from biolink_model.datamodel.pydanticmodel_v2 import CausalGeneToDiseaseAssociation
from koza.utils.testing_utils import mock_koza  # noqa: F401

# Grab parent directory as string, and then add where our ingest code is located, and lastly add to sytem path
parent_dir = '/'.join(os.path.dirname(__file__).split('/')[:-1])
parent_dir = os.path.join(parent_dir, "src/monarch_phenotype_profile_ingest")
sys.path.append(parent_dir)

# Now that our "system" path recognizes our src/ directory we can import our utils and constants
from phenotype_ingest_utils import get_knowledge_sources, get_predicate
from monarch_constants import(BIOLINK_CAUSES,
                              BIOLINK_CONTRIBUTES_TO,
                              BIOLINK_GENE_ASSOCIATED_WITH_CONDITION,
                              INFORES_MEDGEN,
                              INFORES_MONARCHINITIATIVE,
                              INFORES_OMIM,
                              INFORES_ORPHANET)


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
def basic_g2d_entities(mock_koza, row):
    return mock_koza(
        name="gene_to_disease",
        data=row,
        transform_code="./src/monarch_phenotype_profile_ingest/gene_to_disease_transform.py"
    )


def test_hpoa_gene_to_disease(basic_g2d_entities):
    assert len(basic_g2d_entities) == 1
    association = basic_g2d_entities[0]
    assert isinstance(association, CausalGeneToDiseaseAssociation)
    assert association.subject == "NCBIGene:64170"
    assert association.object == "OMIM:212050"
    assert association.predicate == "biolink:causes"
    assert association.primary_knowledge_source == "infores:omim"
    assert association.aggregator_knowledge_source.sort() == ["infores:medgen", "infores:monarchinitiative"].sort()