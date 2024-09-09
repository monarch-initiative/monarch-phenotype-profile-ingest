# General imports
import sys
import uuid  # For generating UUIDs for associations
import subprocess # For counting number of lines in file so we know when to write out all information from koza
import pandas as pd

# Koza and biolink / pydantic imports
from koza.cli_utils import get_koza_app
from biolink_model.datamodel.pydanticmodel_v2 import (GeneToPhenotypicFeatureAssociation,
                                                      KnowledgeLevelEnum,
                                                      AgentTypeEnum)
from phenotype_ingest_utils import phenotype_frequency_to_hpo_term, Frequency


def make_mondo_map(sssom_filepath: str, header=50):
    
    # Read data into memory as df
    df = pd.read_csv(sssom_filepath, sep='\t', header=header)
    
    # Loop through relevant columns and create a map --> mondo
    mondo_map = {}
    for mid, pred, objid in zip(list(df["subject_id"]), list(df["predicate_id"]), list(df["object_id"])):
        
        if pred != "skos:exactMatch":
            continue
        
        if objid not in mondo_map:
            mondo_map.update({objid:mid})

        # Note, currently only a single term does this mesh:D006344 --> MONDO:0006664, MONDO:0020437
        elif mondo_map[objid] != mid:
            print("- Same object id is found to map to multiple mondo ids... {}, {}, {}".format(objid, mondo_map[objid], mid))
            continue

    return mondo_map


# Initiate koza app and mondo map from sssom file
koza_app = get_koza_app("gene_to_phenotype")
mondo_map = koza_app.source.config.sssom_config.lut
print("- MULTIMAPPER ==> mesh:D006344, {}".format(mondo_map["mesh:D006344"]))

map2 = make_mondo_map("./data/mondo.sssom.tsv")

mondo_count = 0
total = 0
while (row := koza_app.get_row()) is not None:
    total += 1
    gene_id = "NCBIGene:" + row["ncbi_gene_id"]
    phenotype_id = row["hpo_id"]

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
            mondo_count += 1
    
    ##quals = ';'.join(list(set([dis_id, org_id])))

    # TO DO: Need to add in the disease_context_qualifier information here (from the commented code above)
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
                                                     ##qualifier=quals)
    
    if total == 312812:
        print("- {}/{} Mapped DiseaseIDs --> MONDO".format(format(mondo_count, ','), format(total, ',')))
        print("- {}/{} Unmapped".format(format(total-mondo_count, ','), format(total, ',')))

        print(len(mondo_map))
        print(len(map2))
    
    koza_app.write(association)