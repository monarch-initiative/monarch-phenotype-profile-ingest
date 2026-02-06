import pytest
from unittest.mock import patch

from biolink_model.datamodel.pydanticmodel_v2 import DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from src.disease_mode_of_inheritance_transform import transform_record

# Mock set of mode-of-inheritance HP terms (avoids loading hp.obo in tests)
MOCK_MODES_OF_INHERITANCE = {
    "HP:0000005",  # Mode of inheritance (umbrella)
    "HP:0000006",  # Autosomal dominant inheritance
    "HP:0000007",  # Autosomal recessive inheritance
    "HP:0001417",  # X-linked inheritance (used in test row)
    "HP:0001423",  # X-linked dominant inheritance
    "HP:0001419",  # X-linked recessive inheritance
}


@pytest.fixture
def d2moi_entities():
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

    koza_transform = KozaTransform(
        mappings={},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    with patch(
        "src.disease_mode_of_inheritance_transform.get_modes_of_inheritance",
        return_value=MOCK_MODES_OF_INHERITANCE,
    ):
        return transform_record(koza_transform, row)


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
