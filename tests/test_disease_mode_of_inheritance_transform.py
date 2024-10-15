import pytest
from biolink_model.datamodel.pydanticmodel_v2 import DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation
from koza.utils.testing_utils import mock_koza  # noqa: F401

INGEST_NAME = "hpoa_disease_mode_of_inheritance"
INGEST_CODE = "./src/monarch_phenotype_profile_ingest/disease_mode_of_inheritance_transform.py"


@pytest.fixture
def d2moi_entities(mock_koza):
    row = {
        "database_id": "OMIM:300425",
        "disease_name": "Autism susceptibility, X-linked 1",
        "qualifier": "",
        "hpo_id": "HP:0001417",
        "reference": "OMIM:300425",
        "evidence": "IEA",
        "onset": "",
        "frequency": "",
        "sex": "",
        "modifier": "",
        "aspect": "I",  # assert 'Inheritance' test record
        "biocuration": "HPO:iea[2009-02-17]",
    }

    return mock_koza(
        name=INGEST_NAME,
        data=row,
        transform_code=INGEST_CODE,
    )


def test_disease_to_mode_of_inheritance_transform(d2moi_entities):
    assert d2moi_entities
    assert len(d2moi_entities) == 1
    association = [
        entity
        for entity in d2moi_entities
        if isinstance(entity, DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation)
    ][0]
    assert association.subject == "OMIM:300425"

    assert association.predicate == "biolink:has_mode_of_inheritance"

    assert association.object == "HP:0001417"
    assert "OMIM:300425" in association.publications
    assert "ECO:0000501" in association.has_evidence  # from local HPOA translation table
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source