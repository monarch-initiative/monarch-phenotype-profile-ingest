import pytest

from biolink_model.datamodel.pydanticmodel_v2 import GeneToPhenotypicFeatureAssociation
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from gene_to_phenotype_transform import transform_record


@pytest.fixture
def mondo_map():
    """
    Mimicks the mondo.sssom file that allows us to map disease_ids back to mondo.
    Original structure had MONDO as keys mapping to OMIM values.
    """
    return {
        "MONDO:0013588": {"subject_id": "OMIM:614129"},
        "MONDO:0009341": {"subject_id": "OMIM:235730"},
        "MONDO:0013212": {"subject_id": "OMIM:613287"}
    }


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
        "publications": "PMID:1234567;OMIM:614129",
        "frequency": "3/10",
        "disease_id": "OMIM:614129",
        "gene_to_disease_association_types": "MENDELIAN"
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
        "publications": "PMID:1234567",
        "frequency": "40.7%",
        "disease_id": "OMIM:235730",
        "gene_to_disease_association_types": "MENDELIAN"
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
        "publications": "PMID:1234567;PMID:2345678",
        "frequency": "-",
        "disease_id": "OMIM:613287",
        "gene_to_disease_association_types": "MENDELIAN"
    }


@pytest.fixture
def basic_hpoa(test_row, mondo_map):
    """
    Koza run for HPOA Gene to Phenotype ingest.
    """
    koza_transform = KozaTransform(
        mappings={"mondo_map": mondo_map},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, test_row)


@pytest.fixture
def basic_hpoa_v2(test_row_v2, mondo_map):
    """
    Koza run for HPOA Gene to Phenotype ingest.
    """
    koza_transform = KozaTransform(
        mappings={"mondo_map": mondo_map},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, test_row_v2)


@pytest.fixture
def basic_hpoa_v3(test_row_v3, mondo_map):
    """
    Koza run for HPOA Gene to Phenotype ingest.
    """
    koza_transform = KozaTransform(
        mappings={"mondo_map": mondo_map},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, test_row_v3)


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
    assert association
    assert association.subject == "NCBIGene:8192"
    assert association.object == "HP:0000252"
    assert association.predicate == "biolink:has_phenotype"
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source

    # Frequency information
    assert association.frequency_qualifier == None
    assert association.has_percentage == 30.0
    assert association.has_quotient == 0.3
    assert association.has_count == 3
    assert association.has_total == 10
    assert association.disease_context_qualifier == "OMIM:614129"
    assert association.publications == ["PMID:1234567", "OMIM:614129"]


# Frequency data is in the form of percentage (i.e. 55% or 40.7% etc...)
def test_hpoa_g2p_association_v2(basic_hpoa_v2):
    assert basic_hpoa_v2
    assert len(basic_hpoa_v2) == 1
    association = [entity for entity in basic_hpoa_v2 if isinstance(entity, GeneToPhenotypicFeatureAssociation)][0]
    assert association
    assert association.subject == "NCBIGene:9839"
    assert association.object == "HP:0012429"
    assert association.predicate == "biolink:has_phenotype"
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source

    assert association.frequency_qualifier == None
    assert association.has_percentage == 40.7
    assert round(association.has_quotient, 3) == .407
    assert association.has_count == None
    assert association.has_total == None
    assert association.disease_context_qualifier == "OMIM:235730"
    assert association.publications == ["PMID:1234567"]


# Frequency data is in the form of "-" (i.e. it does not exist)
def test_hpoa_g2p_association_v3(basic_hpoa_v3):
    assert basic_hpoa_v3
    assert len(basic_hpoa_v3) == 1
    association = [entity for entity in basic_hpoa_v3 if isinstance(entity, GeneToPhenotypicFeatureAssociation)][0]
    assert association
    assert association.subject == "NCBIGene:16"
    assert association.object == "HP:0001284"
    assert association.predicate == "biolink:has_phenotype"
    assert association.frequency_qualifier == None
    assert association.has_percentage == None
    assert association.has_quotient == None
    assert association.has_count == None
    assert association.has_total == None
    assert association.primary_knowledge_source == "infores:hpo-annotations"
    assert association.disease_context_qualifier == "OMIM:613287"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source
    assert association.publications == ["PMID:1234567", "PMID:2345678"]
