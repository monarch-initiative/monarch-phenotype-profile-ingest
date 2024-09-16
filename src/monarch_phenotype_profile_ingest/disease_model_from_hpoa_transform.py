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
  --source src/monarch_phenotype_profile_ingest/disease_phenotype.yaml \
  --output-format tsv
"""

# General imports
import sys
from typing import Optional, List
import uuid

# Koza, biolink / pydantic imports, and monarch ingest utilis
from koza.cli_utils import get_koza_app
from biolink_model.datamodel.pydanticmodel_v2 import (DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation,
                                                      DiseaseToPhenotypicFeatureAssociation,
                                                      KnowledgeLevelEnum,
                                                      AgentTypeEnum)
from phenotype_ingest_utils import phenotype_frequency_to_hpo_term, Frequency



def get_disease_primary_knowledge_source(disease_id: str) -> str:
    """
    Attempts to find out if id belongs to omim, orphanet or decipher 
    and returns the relevant biolink slot input
    """
    if disease_id.startswith("OMIM"):
        return "infores:omim"
    elif disease_id.startswith("ORPHA") or "orpha" in disease_id.lower():
        return "infores:orphanet"
    elif disease_id.startswith("DECIPHER"):
        return "infores:decipher"
    else:
        raise ValueError(f"Unknown disease ID prefix for {disease_id}, can't set primary_knowledge_source")


# Initiate koza app
koza_app = get_koza_app("disease_model_from_hpoa")

count = 0
while (row := koza_app.get_row()) is not None:

    #############################################
    ### Assign variables from row information ###

    association = "NA"
    disease_id = row["database_id"].replace("ORPHA:", "Orphanet:") # match `Orphanet` as used in Mondo SSSOM
    hpo_id = row["hpo_id"]
    onset = row["onset"]
    
    # Three letter ECO code to ECO class based on HPO documentation
    evidence_curie = koza_app.translation_table.resolve_term(row["evidence"])

    # Publications
    publications_field: str = row["reference"]
    publications: List[str] = publications_field.split(";")

    # female --> PATO:0000383, male --> PATO:0000384
    sex: Optional[str] = row["sex"]  # may be translated by local table
    sex_qualifier = koza_app.translation_table.resolve_term(sex) if sex else None

    # Raw frequencies - HPO term curies, ratios, percentages - normalized to HPO terms
    frequency: Frequency = phenotype_frequency_to_hpo_term(row["frequency"])

    # Predicate negation
    negated: Optional[bool]
    if row["qualifier"] == "NOT":
        negated = True
    else:
        negated = False


    ############################
    ### Disease to Phenotype ###
    if row["aspect"] == "P":
        
        predicate = "biolink:has_phenotype"
        assert hpo_id, "HPOA Disease to Phenotype has missing HP ontology ('HPO_ID') field identifier?"

        # don't populate the reference with the database_id / disease id
        publications = [p for p in publications if not p == row["database_id"]]

        primary_knowledge_source = get_disease_primary_knowledge_source(disease_id)

        # Association/Edge
        association = DiseaseToPhenotypicFeatureAssociation(id="uuid:" + str(uuid.uuid1()),
                                                            subject=disease_id,
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
    

    ###################################
    ### Disease mode of Inheritance ###
    elif row["aspect"] == "I":

        # Object: Actually a Genetic Inheritance (as should be specified by a suitable HPO term)
        # TODO: perhaps load the proper (Genetic Inheritance) node concepts into the Monarch Graph (simply as Ontology terms?).
        # We ignore records that don't map to a known HPO term for Genetic Inheritance
        # (as recorded in the locally bound 'hpoa-modes-of-inheritance' table)
        if hpo_id and hpo_id in koza_app.translation_table.local_table:

            # Predicate (canonical direction)
            predicate = "biolink:has_mode_of_inheritance"

            # Filter out some weird NCBI web endpoints
            publications = [p for p in publications if not p.startswith("http")]

            # Association/Edge
            association = DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation(id="uuid:" + str(uuid.uuid1()),
                                                                                    subject=disease_id,
                                                                                    predicate=predicate,
                                                                                    object=hpo_id,
                                                                                    publications=publications,
                                                                                    has_evidence=[evidence_curie],
                                                                                    aggregator_knowledge_source=["infores:monarchinitiative"],
                                                                                    primary_knowledge_source="infores:hpo-annotations",
                                                                                    knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
                                                                                    agent_type=AgentTypeEnum.manual_agent)
    
    count += 1
    if type(association) != type("NA"):
        koza_app.write(association)