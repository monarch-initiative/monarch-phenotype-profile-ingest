# For generating UUIDs for associations
import uuid

# Koza and biolink / pydantic imports
from koza.cli_utils import get_koza_app
from biolink_model.datamodel.pydanticmodel_v2 import (GeneToPhenotypicFeatureAssociation,
                                                      KnowledgeLevelEnum,
                                                      AgentTypeEnum)
from phenotype_ingest_utils import phenotype_frequency_to_hpo_term, Frequency


# TO DO: Once biolink is updated with the disease_context_qualifier slot we need to update the association we make
# https://github.com/biolink/biolink-model/pull/1524


# Initiate koza app and mondo map from sssom file
koza_app = get_koza_app("gene_to_phenotype")

try:
    # For ingest (this data is unavailable for mock_koza)
    mondo_map = koza_app.source.config.sssom_config.lut
except:
    # For testing ingest (allows mock_koza to bring in map_cache)
    mondo_map = koza_app.get_map('mondo_map')


while (row := koza_app.get_row()) is not None:
    gene_id = "NCBIGene:" + row["ncbi_gene_id"]
    phenotype_id = row["hpo_id"]

    # Set mondo map (we don't do it above, because the testing harness does not like it..)

    # No frequency data provided
    if row["frequency"] == "-":
        frequency = Frequency()
    else:
        # Raw frequencies - HPO term curies, ratios, percentages - normalized to HPO terms
        frequency: Frequency = phenotype_frequency_to_hpo_term(row["frequency"])
    
    # Convert to mondo id if possible, otherwise leave as is
    org_id = row["disease_id"].replace("ORPHA:", "Orphanet:")
    dis_id = org_id
    if dis_id in mondo_map:
        if "MONDO" in mondo_map[dis_id]:
            dis_id = mondo_map[dis_id]["MONDO"]
    
    # TO DO: we may want to incorporate the original disease id somehow?
    # TO DO: Need to add in the disease_context_qualifier information here once biolink is updated

    association = GeneToPhenotypicFeatureAssociation(id="uuid:" + str(uuid.uuid1()),
                                                     subject=gene_id,
                                                     predicate="biolink:has_phenotype",
                                                     object=phenotype_id,
                                                     aggregator_knowledge_source=["infores:monarchinitiative"],
                                                     primary_knowledge_source="infores:hpo-annotations",
                                                     knowledge_level=KnowledgeLevelEnum.logical_entailment,
                                                     agent_type=AgentTypeEnum.automated_agent,
                                                    
                                                     # New data
                                                     frequency_qualifier=frequency.frequency_qualifier if frequency.frequency_qualifier else None,
                                                     has_percentage=frequency.has_percentage,
                                                     has_quotient=frequency.has_quotient,
                                                     has_count=frequency.has_count,
                                                     has_total=frequency.has_total)

                                                     # For this ingest, will either be mondo or orphanet id (i.e. MONDO:0004979) 
                                                     #disease_context_qualifier=dis_id)
    
    koza_app.write(association)