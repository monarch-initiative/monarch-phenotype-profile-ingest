"""
The [Human Phenotype Ontology](http://human-phenotype-ontology.org) group
curates and assembles over 115,000 annotations to hereditary diseases
using the HPO ontology. Here we create Biolink associations
between diseases and phenotypic features, together with their evidence,
and age of onset and frequency (if known).

The parser currently only processes the "abnormal" annotations.
Association to "remarkable normality" will be added in the near future.

filters:
  - inclusion: 'include'
    column: 'Aspect'
    filter_code: 'eq'
    value: 'P'

We are only keeping 'P' == 'phenotypic anomaly' records.

Usage:
poetry run koza transform \
  --global-table data/translation_table.yaml \
  --local-table src/monarch_phenotype_profile_ingest/hpoa_translation.yaml \
  --source src/monarch_phenotype_profile_ingest/disease_to_phenotype.yaml \
  --output-format tsv
"""

from typing import Optional, List
import uuid

# Koza, biolink / pydantic imports, and monarch ingest utilis
from koza.cli_utils import get_koza_app
from biolink_model.datamodel.pydanticmodel_v2 import (DiseaseToPhenotypicFeatureAssociation,
                                                      KnowledgeLevelEnum,
                                                      AgentTypeEnum)
from phenotype_ingest_utils import (evidence_to_eco, 
                                    sex_format,
                                    sex_to_pato,
                                    hpo_to_mode_of_inheritance,
                                    phenotype_frequency_to_hpo_term, 
                                    Frequency)


def get_primary_knowledge_source(disease_id: str) -> str:
    if disease_id.startswith("OMIM"):
        return "infores:omim"
    elif disease_id.startswith("ORPHA") or "orpha" in disease_id.lower():
        return "infores:orphanet"
    elif disease_id.startswith("DECIPHER"):
        return "infores:decipher"
    else:
        raise ValueError(f"Unknown disease ID prefix for {disease_id}, can't set primary_knowledge_source")


koza_app = get_koza_app("disease_to_phenotype")

while (row := koza_app.get_row()) is not None:

    # Nodes
    disease_id = row["database_id"]

    predicate = "biolink:has_phenotype"

    hpo_id = row["hpo_id"]
    assert hpo_id, "HPOA Disease to Phenotype has missing HP ontology ('HPO_ID') field identifier?"

    # Predicate negation
    negated: Optional[bool]
    if row["qualifier"] == "NOT":
        negated = True
    else:
        negated = False

    # Annotations

    # Translations to curies
    # Three letter ECO code to ECO class based on hpo documentation
    evidence_curie = evidence_to_eco[row["evidence"]]

    # female -> PATO:0000383
    # male -> PATO:0000384
    sex: Optional[str] = row["sex"]  # may be translated by local table
    sex_qualifier = sex_to_pato[sex_format[sex]] if sex in sex_format else None
    #sex_qualifier = sex_format[sex] if sex in sex_format else None

    onset = row["onset"]

    # Raw frequencies - HPO term curies, ratios, percentages - normalized to HPO terms
    frequency: Frequency = phenotype_frequency_to_hpo_term(row["frequency"])

    # Publications
    publications_field: str = row["reference"]
    publications: List[str] = publications_field.split(";")

    # don't populate the reference with the database_id / disease id
    publications = [p for p in publications if not p == row["database_id"]]

    primary_knowledge_source = get_primary_knowledge_source(disease_id )

    # Association/Edge
    association = DiseaseToPhenotypicFeatureAssociation(id="uuid:" + str(uuid.uuid1()),
                                                        subject=disease_id.replace("ORPHA:", "Orphanet:"),  # match `Orphanet` as used in Mondo SSSOM
                                                        predicate=predicate,
                                                        negated=negated,
                                                        object=hpo_id,
                                                        publications=publications,
                                                        has_evidence=[evidence_curie],
                                                        sex_qualifier=sex_qualifier,
                                                        onset_qualifier=onset,
                                                        has_percentage=frequency.has_percentage,
                                                        has_quotient=frequency.has_quotient,
                                                        frequency_qualifier=frequency.frequency_qualifier if frequency.frequency_qualifier else None,
                                                        has_count=frequency.has_count,
                                                        has_total=frequency.has_total,
                                                        aggregator_knowledge_source=["infores:monarchinitiative","infores:hpo-annotations"],
                                                        primary_knowledge_source=primary_knowledge_source,
                                                        knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
                                                        agent_type=AgentTypeEnum.manual_agent)

    koza_app.write(association)