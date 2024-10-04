import pytest
from biolink_model.datamodel.pydanticmodel_v2 import GeneToPhenotypicFeatureAssociation
from koza.utils.testing_utils import mock_koza  # noqa: F401



@pytest.fixture
def map_cache():
    """
    Mimicks the mondo.sssom file that allows us to map disease_ids back to mondo
    NOTE that the actual sssom data within this ingest is stored in a datastructue that mock koza doesn't generate
    Therefore, we supply the same information we would have any ways done, as a koza map instead.
    This requires a minor alteration to the ingest_transform.py script itself
    """
    return {"mondo_map": {"MONDO:0013588":"OMIM:614129",
                          "MONDO:0009341":"OMIM:235730",
                          "MONDO:0013212":"OMIM:613287"}}


@pytest.fixture
def source_name():
    """
    :return: string source name of HPOA Gene to Phenotype ingest
    """
    return "gene_to_phenotype"


@pytest.fixture
def script():
    """
    :return: string path to HPOA Gene to Phenotype ingest script
    """
    return "./src/monarch_phenotype_profile_ingest/gene_to_phenotype_transform.py"


@pytest.fixture
def test_row():
    """
    :return: Test HPOA Gene to Phenotype data row.
    """
    return {
        "ncbi_gene_id": "8192",
        "gene_symbol": "CLPP",
        "hpo_id": "HP:0000252",
        "hpo_name": "Microcephaly",

        "frequency": "3/10",
        "disease_id": "OMIM:614129"
    }


@pytest.fixture
def test_row_v2():
    """
    :return: Test HPOA Gene to Phenotype data row.
    """
    return {
        "ncbi_gene_id": "9839",
        "gene_symbol": "ZEB2",
        "hpo_id": "HP:0012429",
        "hpo_name": "Aplasia/Hypoplasia of the cerebral white matter",

        "frequency": "40.7%",
        "disease_id": "OMIM:235730"
    }

@pytest.fixture
def test_row_v3():
    """
    :return: Test HPOA Gene to Phenotype data row.
    """

    return {
        "ncbi_gene_id": "16",
        "gene_symbol": "AARS1",
        "hpo_id": "HP:0001284",
        "hpo_name": "Areflexia",

        "frequency": "-",
        "disease_id": "OMIM:613287"
    }

@pytest.fixture
def basic_hpoa(mock_koza, source_name, script, test_row, map_cache):
    """
    Mock Koza run for HPOA Gene to Phenotype ingest.

    :param mock_koza:
    :param source_name:
    :param test_row:
    :param script:

    :return: mock_koza application
    """
    return mock_koza(name=source_name, data=test_row, transform_code=script, map_cache=map_cache)

@pytest.fixture
def basic_hpoa_v2(mock_koza, source_name, script, test_row_v2, map_cache):
    """
    Mock Koza run for HPOA Gene to Phenotype ingest.

    :param mock_koza:
    :param source_name:
    :param test_row:
    :param script:

    :return: mock_koza application
    """
    return mock_koza(name=source_name, data=test_row_v2, transform_code=script, map_cache=map_cache)


@pytest.fixture
def basic_hpoa_v3(mock_koza, source_name, script, test_row_v3, map_cache):
    """
    Mock Koza run for HPOA Gene to Phenotype ingest.

    :param mock_koza:
    :param source_name:
    :param test_row:
    :param script:

    :return: mock_koza application
    """
    return mock_koza(name=source_name, data=test_row_v3, transform_code=script, map_cache=map_cache)


@pytest.mark.parametrize("cls", [GeneToPhenotypicFeatureAssociation])
def test_confirm_one_of_each_classes(cls, basic_hpoa, basic_hpoa_v2, basic_hpoa_v3):

    class_entities = [entity for entity in basic_hpoa if isinstance(entity, cls)]
    assert class_entities
    assert len(class_entities) == 1
    assert class_entities[0]

    class_entities = [entity for entity in basic_hpoa_v2 if isinstance(entity, cls)]
    assert class_entities
    assert len(class_entities) == 1
    assert class_entities[0]

    class_entities = [entity for entity in basic_hpoa_v3 if isinstance(entity, cls)]
    assert class_entities
    assert len(class_entities) == 1
    assert class_entities[0]


# Frequency data is in the form of counts (i.e. 3/10, or 56/100 etc...)
def test_hpoa_g2p_association(basic_hpoa):

    assert basic_hpoa
    assert len(basic_hpoa) == 1
    association = [entity for entity in basic_hpoa if isinstance(entity, GeneToPhenotypicFeatureAssociation)][0]
    assert len(basic_hpoa) == 1
    assert basic_hpoa[0]
    assert basic_hpoa[0].subject == "NCBIGene:8192"
    assert basic_hpoa[0].object == "HP:0000252"
    assert basic_hpoa[0].predicate == "biolink:has_phenotype"
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source

    # Newest additions (frequency information)
    assert basic_hpoa[0].frequency_qualifier == None
    assert basic_hpoa[0].has_percentage == 30.0
    assert basic_hpoa[0].has_quotient == 0.3
    assert basic_hpoa[0].has_count == 3
    assert basic_hpoa[0].has_total == 10

# Frequency data is in the form of percentage (i.e. 55% or 40.7% etc...)
def test_hpoa_g2p_association_v2(basic_hpoa_v2):

    assert basic_hpoa_v2
    assert len(basic_hpoa_v2) == 1
    association = [entity for entity in basic_hpoa_v2 if isinstance(entity, GeneToPhenotypicFeatureAssociation)][0]
    assert len(basic_hpoa_v2) == 1
    assert basic_hpoa_v2[0]
    assert basic_hpoa_v2[0].subject == "NCBIGene:9839"
    assert basic_hpoa_v2[0].object == "HP:0012429"
    assert basic_hpoa_v2[0].predicate == "biolink:has_phenotype"
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source

    # Newest additions (frequency information)
    assert basic_hpoa_v2[0].frequency_qualifier == None
    assert basic_hpoa_v2[0].has_percentage == 40.7
    assert round(basic_hpoa_v2[0].has_quotient, 3) == .407
    assert basic_hpoa_v2[0].has_count == None
    assert basic_hpoa_v2[0].has_total == None

# Frequency data is in the form of "-" (i.e. it does not exist)
def test_hpoa_g2p_association_v3(basic_hpoa_v3):

    assert basic_hpoa_v3
    assert len(basic_hpoa_v3) == 1
    association = [entity for entity in basic_hpoa_v3 if isinstance(entity, GeneToPhenotypicFeatureAssociation)][0]
    assert len(basic_hpoa_v3) == 1
    assert basic_hpoa_v3[0]
    assert basic_hpoa_v3[0].subject == "NCBIGene:16"
    assert basic_hpoa_v3[0].object == "HP:0001284"
    assert basic_hpoa_v3[0].predicate == "biolink:has_phenotype"
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source

    # Newest additions (frequency information)
    assert basic_hpoa_v3[0].frequency_qualifier == None
    assert basic_hpoa_v3[0].has_percentage == None
    assert basic_hpoa_v3[0].has_quotient == None
    assert basic_hpoa_v3[0].has_count == None
    assert basic_hpoa_v3[0].has_total == None