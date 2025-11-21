import uuid

import koza
from biolink_model.datamodel.pydanticmodel_v2 import (
    CausalGeneToDiseaseAssociation,
    CorrelatedGeneToDiseaseAssociation,
    KnowledgeLevelEnum,
    AgentTypeEnum
)
from monarch_phenotype_profile_ingest.monarch_constants import INFORES_MONARCHINITIATIVE, BIOLINK_CAUSES
from monarch_phenotype_profile_ingest.phenotype_ingest_utils import get_knowledge_sources, get_predicate


@koza.transform_record()
def transform_record(koza_transform, row):
    # Handle weird koza behavior that is reading the header as a data row no matter how the reader is configured
    if row["ncbi_gene_id"] == "ncbi_gene_id":
        return []
    gene_id = row["ncbi_gene_id"]
    disease_id = row["disease_id"].replace("ORPHA:", "Orphanet:")

    predicate = get_predicate(row["association_type"])
    primary_knowledge_source, aggregator_knowledge_source = get_knowledge_sources(
        row["source"],
        INFORES_MONARCHINITIATIVE
    )

    if predicate == BIOLINK_CAUSES:
        association_class = CausalGeneToDiseaseAssociation
    else:
        association_class = CorrelatedGeneToDiseaseAssociation

    association = association_class(
        id="uuid:" + str(uuid.uuid1()),
        subject=gene_id,
        predicate=predicate,
        object=disease_id,
        primary_knowledge_source=primary_knowledge_source,
        aggregator_knowledge_source=aggregator_knowledge_source,
        knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
        agent_type=AgentTypeEnum.manual_agent
    )

    return [association]
