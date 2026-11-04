import uuid

import koza
from biolink_model.datamodel.pydanticmodel_v2 import (
    AgentTypeEnum,
    CausalGeneToDiseaseAssociation,
    CorrelatedGeneToDiseaseAssociation,
    KnowledgeLevelEnum,
)

from src.orphanet_gene_to_disease_utils import (
    get_orphanet_association_type_code,
    get_orphanet_form_qualifier,
    get_orphanet_predicate,
)
from src.phenotype_ingest_utils import BIOLINK_CAUSES, INFORES_MONARCHINITIATIVE, INFORES_ORPHANET


@koza.transform_record()
def transform_record(koza_transform, row):
    # Rows whose gene could not be resolved to an NCBIGene id (withdrawn HGNC locus entries,
    # snoRNA clusters) are reported by the preprocess step and skipped here.
    if not row["ncbi_gene_id"]:
        return []

    association_type = row["association_type"]
    association_status = row["association_status"]
    type_code = get_orphanet_association_type_code(association_type, association_status)
    predicate = get_orphanet_predicate(type_code)
    publications = [pub for pub in (row["publications"] or "").split(";") if pub]

    common = dict(
        id="uuid:" + str(uuid.uuid1()),
        subject=row["ncbi_gene_id"],
        predicate=predicate,
        object=row["disease_id"],
        original_subject=row["hgnc_id"] or None,
        original_predicate=association_type,
        qualifiers=[association_status],
        publications=publications,
        primary_knowledge_source=INFORES_ORPHANET,
        aggregator_knowledge_source=[INFORES_MONARCHINITIATIVE],
        knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
        agent_type=AgentTypeEnum.manual_agent,
    )

    if predicate == BIOLINK_CAUSES:
        association = CausalGeneToDiseaseAssociation(
            **common,
            subject_form_or_variant_qualifier=get_orphanet_form_qualifier(association_type),
        )
    else:
        association = CorrelatedGeneToDiseaseAssociation(**common)

    return [association]
