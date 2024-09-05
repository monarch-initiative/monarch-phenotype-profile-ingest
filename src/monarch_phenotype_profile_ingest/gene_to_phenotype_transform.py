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


def count_lines_in_file(file_path):
    """
    Uses subprocess to grab the line count of a file and return it as an integer 
    """

    # The output is in the format: 'number_of_lines filename', so we split and take the first part
    result = subprocess.run(['wc', '-l', file_path], stdout=subprocess.PIPE, text=True)
    line_count = int(result.stdout.split()[0])
    return line_count


def make_mondo_map(sssom_filepath, header=50):
    
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
            continue
            #print("- Same object id is found to map to multiple mondo ids... {}, {}, {}".format(objid, mondo_map[objid], mid))
    
    return mondo_map


# Initiate koza app and mondo map
koza_app = get_koza_app("gene_to_phenotype")
mondo_map = make_mondo_map("./data/mondo.sssom.tsv")
line_count = count_lines_in_file(koza_app.source.config.files[0]) - 1 # Subtract 1 for header information

count = 0
g2p = {}
while (row := koza_app.get_row()) is not None:
    gene_id = "NCBIGene:" + row["ncbi_gene_id"]
    phenotype_id = row["hpo_id"]

    # Nothing provided
    if row["frequency"] == "-":
        frequency = Frequency()
    else:
        # Raw frequencies - HPO term curies, ratios, percentages - normalized to HPO terms
        frequency: Frequency = phenotype_frequency_to_hpo_term(row["frequency"])
    
    # Convert to mondo id if possible, otherwise leave as is
    org_id = row["disease_id"].replace("ORPHA:", "Orphanet:")
    dis_id = org_id
    if dis_id in mondo_map:
        dis_id = mondo_map[dis_id]

    # Create this association if it doesn't already exist and store so it can be updated (if necessary) later on in the file
    key = (gene_id, phenotype_id, dis_id)
    if key not in g2p:
        quals = ';'.join(list(set([dis_id, org_id])))
        association = GeneToPhenotypicFeatureAssociation(id="uuid:" + str(uuid.uuid1()),
                                                         subject=gene_id,
                                                         predicate="biolink:has_phenotype",
                                                         object=phenotype_id,
                                                         aggregator_knowledge_source=["infores:monarchinitiative"],
                                                         primary_knowledge_source="infores:hpo-annotations",
                                                         knowledge_level=KnowledgeLevelEnum.logical_entailment,
                                                         agent_type=AgentTypeEnum.automated_agent,
                                                         frequency_qualifier=frequency.frequency_qualifier if frequency.frequency_qualifier else None,
                                                         qualifier=quals)
        g2p.update({key:association})
        
    # Otherwise, update the frequency qualifier for the stored association
    else:
        quals = ';'.join(list(set([dis_id, org_id]+g2p[key].qualifier.split(';'))))
        g2p[key].qualifier = quals
        if g2p[key].frequency_qualifier == None:
            g2p[key].frequency_qualifier = frequency.frequency_qualifier if frequency.frequency_qualifier else None

    # Don't write out anything until we reach the very last line of the file
    # This ensures that each association we make gets all of the relevant information pulled in (the proper frequency_qualifier in this case is what we are trying to capture along with the different disease ids)
    count += 1
    if count == line_count:
        for k, assco in g2p.items():
            koza_app.write(assco)
    
    # Sanity check
    if count > line_count:
        print("- ERROR, Additional {} lines found... Most likely a discrepancy with the header line(s) expectations".format(count-line_count))