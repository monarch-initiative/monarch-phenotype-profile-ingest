"""
The [Human Phenotype Ontology](http://human-phenotype-ontology.org) group
curates and assembles over 115,000 annotations to hereditary diseases
using the HPO ontology. Here we create Biolink associations
between diseases and their mode of inheritance.

This parser only processes out the "inheritance" (aspect == 'I') annotation records.

filters:
  - inclusion: 'include'
    column: 'aspect'
    filter_code: 'eq'
    value: 'I'

Usage:
poetry run koza transform \
  --global-table data/translation_table.yaml \
  --local-table src/monarch_phenotype_profile_ingest/hpoa_translation.yaml \
  --source src/monarch_phenotype_profile_ingesthpoa/disease_mode_of_inheritance.yaml \
  --output-format tsv
"""

from typing import List
import uuid

import koza
from biolink_model.datamodel.pydanticmodel_v2 import (
    DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation,
    KnowledgeLevelEnum,
    AgentTypeEnum
)
from src.phenotype_ingest_utils import (
    evidence_to_eco,
    read_ontology_to_exclusion_terms
)
from loguru import logger

_modes_of_inheritance = None


def get_modes_of_inheritance():
    """Load HP mode of inheritance terms on first access."""
    global _modes_of_inheritance
    if _modes_of_inheritance is None:
        _modes_of_inheritance = read_ontology_to_exclusion_terms(
            "data/hp.obo", umbrella_term="HP:0000005", include=True
        )
    return _modes_of_inheritance


@koza.transform_record()
def transform_record(koza_transform, row):
    # Object: Actually a Genetic Inheritance (as should be specified by a suitable HPO term)
    # TODO: perhaps load the proper (Genetic Inheritance) node concepts into the Monarch Graph (simply as Ontology terms?).
    hpo_id = row["hpo_id"]

    # We ignore records that don't map to a known HPO term for Genetic Inheritance
    # (as recorded in the locally bound 'hpoa-modes-of-inheritance' table)
    if hpo_id and hpo_id in get_modes_of_inheritance():

        # Nodes

        # Subject: Disease
        disease_id = row["database_id"]

        # Predicate (canonical direction)
        predicate = "biolink:has_mode_of_inheritance"

        # Annotations

        # Three letter ECO code to ECO class based on HPO documentation
        evidence_curie = evidence_to_eco[row["evidence"]]

        # Publications
        publications_field: str = row["reference"]
        publications: List[str] = publications_field.split(";")

        # Filter out some weird NCBI web endpoints
        publications = [p for p in publications if not p.startswith("http")]

        # Association/Edge
        association = DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation(
            id="uuid:" + str(uuid.uuid1()),
            subject=disease_id,
            predicate=predicate,
            object=hpo_id,
            publications=publications,
            has_evidence=[evidence_curie],
            aggregator_knowledge_source=["infores:monarchinitiative"],
            primary_knowledge_source="infores:hpo-annotations",
            knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
            agent_type=AgentTypeEnum.manual_agent
        )
        return [association]

    else:
        logger.warning(f"HPOA ID field value '{str(hpo_id)}' is missing or an invalid disease mode of inheritance?")
        return []
