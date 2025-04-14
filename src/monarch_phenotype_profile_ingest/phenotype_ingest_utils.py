"""
HPOA processing utility methods
"""

from typing import Optional, List, Dict
from pronto import Ontology


from loguru import logger
from pydantic import BaseModel

from monarch_constants import (INFORES_MEDGEN,
                               INFORES_OMIM,
                               INFORES_ORPHANET,
                               BIOLINK_CAUSES,
                               BIOLINK_CONTRIBUTES_TO,
                               BIOLINK_GENE_ASSOCIATED_WITH_CONDITION)


# Evidence Code translations - https://www.ebi.ac.uk/ols4/ontologies/eco
evidence_to_eco: Dict = {"IEA": "ECO:0000501", # "inferred from electronic annotation",
                         "PCS": "ECO:0006017", # "published clinical study evidence",
                         "TAS": "ECO:0000304", # "traceable author statement",
                         "ICE": "ECO:0006019"} # "individual clinical experience evidence"}

# Sex (right now both all uppercase and all lowercase
sex_format: Dict = {"male": "male",
                    "MALE": "male",
                    "female": "female",
                    "FEMALE": "female"}

sex_to_pato: Dict = {"female": "PATO:0000383",
                     "male":   "PATO:0000384"}


class FrequencyHpoTerm(BaseModel):
    """
    Data class to store relevant information
    """
    curie: str
    name: str
    lower: float
    upper: float


class Frequency(BaseModel):
    """
    Converts fields to pydantic field declarations
    """
    frequency_qualifier: Optional[str] = None
    has_percentage: Optional[float] = None
    has_quotient: Optional[float] = None
    has_count: Optional[int] = None
    has_total: Optional[int] = None


# HPO "HP:0040279": representing the frequency of phenotypic abnormalities within a patient cohort.
hpo_term_to_frequency: Dict = {"HP:0040280": FrequencyHpoTerm(curie="HP:0040280", 
                                                              name="Obligate", 
                                                              lower=100.0, 
                                                              upper=100.0), # Always present,i.e. in 100% of the cases.
                               "HP:0040281": FrequencyHpoTerm(curie="HP:0040281", 
                                                              name="Very frequent", 
                                                              lower=80.0, 
                                                              upper=99.0), # Present in 80% to 99% of the cases.
                               "HP:0040282": FrequencyHpoTerm(curie="HP:0040282", 
                                                              name="Frequent", 
                                                              lower=30.0, 
                                                              upper=79.0),# Present in 30% to 79% of the cases.
                               "HP:0040283": FrequencyHpoTerm(curie="HP:0040283", 
                                                              name="Occasional", 
                                                              lower=5.0, 
                                                              upper=29.0), # Present in 5% to 29% of the cases.
                               "HP:0040284": FrequencyHpoTerm(curie="HP:0040284", 
                                                              name="Very rare", 
                                                              lower=1.0, 
                                                              upper=4.0), # Present in 1% to 4% of the cases.
                               "HP:0040285": FrequencyHpoTerm(curie="HP:0040285", 
                                                              name="Excluded", 
                                                              lower=0.0, 
                                                              upper=0.0)}  # Present in 0% of the cases.}


def get_hpo_term(hpo_id: str) -> Optional[FrequencyHpoTerm]:
    """
    Leverages the global hpo_term_to_frequency dict to grab the relevant object
    """
    if hpo_id:
        return hpo_term_to_frequency[hpo_id] if hpo_id in hpo_term_to_frequency else None
    else:
        return None


def map_percentage_frequency_to_hpo_term(percentage_or_quotient: float) -> Optional[FrequencyHpoTerm]:
    """
    Map phenotypic percentage frequency to a corresponding HPO term corresponding to (HP:0040280 to HP:0040285).

    :param percentage_or_quotient: int, should be in range 0.0 to 100.0
    :return: str, HPO term mapping onto percentage range of term definition; None if outside range
    """
    for hpo_id, details in hpo_term_to_frequency.items():
        if details.lower <= percentage_or_quotient <= details.upper:
            return details

    return None


def phenotype_frequency_to_hpo_term(frequency_field: Optional[str]) -> Frequency:
    """
    Maps a raw frequency field onto HPO, for consistency. This is needed since the **phenotypes.hpoa**
    file field #8 which tracks phenotypic frequency, has a variable values. There are three allowed options for this field:

    1. A term-id from the HPO-sub-ontology below the term “Frequency” (HP:0040279). (since December 2016 ; before was a mixture of values). The terms for frequency are in alignment with Orphanet;
    2. A percentage value such as 17%.
    3. A count of patients affected within a cohort. For instance, 7/13 would indicate that 7 of the 13 patients with the specified disease were found to have the phenotypic abnormality referred to by the HPO term in question in the study referred to by the DB_Reference;

        :param frequency_field: str, raw frequency value in one of the three above forms
        :return: Optional[FrequencyHpoTerm, float, float], raw frequency mapped to its HPO term, quotient or percentage
                 respectively (as applicable); return None if unmappable;
                 percentage and/or quotient returned are also None, if not applicable
    """
    hpo_term: Optional[FrequencyHpoTerm] = None
    quotient: Optional[float] = None
    percentage: Optional[float] = None
    has_count: Optional[int] = None
    has_total: Optional[int] = None
    if frequency_field:
        try:

            if frequency_field.startswith("HP:"):
                hpo_term = get_hpo_term(hpo_id=frequency_field)

            elif frequency_field.endswith("%"):
                percentage = float(frequency_field.removesuffix("%"))
                quotient = percentage / 100.0

            else:
                # assume a ratio
                ratio_parts = frequency_field.split("/")
                has_count = int(ratio_parts[0])
                has_total = int(ratio_parts[1])
                quotient = float(has_count / has_total)
                percentage = quotient * 100.0

        except Exception:
            # expected ratio not recognized
            logger.error(f"hpoa_frequency(): invalid frequency ratio '{frequency_field}'")
            frequency_field = None
    else:
        # may be None, if original field was empty or has an invalid value
        return Frequency()

    return Frequency(
        frequency_qualifier=hpo_term.curie if hpo_term else None,
        has_percentage=percentage,
        has_quotient=quotient,
        has_count=has_count,
        has_total=has_total,
    )


def get_knowledge_sources(original_source: str, additional_source: str) -> (str, List[str]):
    """
    Return a tuple of the primary_knowledge_source and original_knowledge_source
    """
    _primary_knowledge_source: str = ""
    _aggregator_knowledge_source: List[str] = []

    if additional_source is not None:
        _aggregator_knowledge_source.append(additional_source)

    if "medgen" in original_source:
        _aggregator_knowledge_source.append(INFORES_MEDGEN)
        _primary_knowledge_source = INFORES_OMIM
    elif "orphadata" in original_source:
        _primary_knowledge_source = INFORES_ORPHANET

    if _primary_knowledge_source == "":
        raise ValueError(f"Unknown knowledge source: {original_source}")

    return _primary_knowledge_source, _aggregator_knowledge_source


def get_predicate(original_predicate: str) -> str:
    """
    Convert the association column into a Biolink Model predicate
    """
    if original_predicate == 'MENDELIAN':
        return BIOLINK_CAUSES
    elif original_predicate == 'POLYGENIC':
        return BIOLINK_CONTRIBUTES_TO
    elif original_predicate == 'UNKNOWN':
        return BIOLINK_GENE_ASSOCIATED_WITH_CONDITION
    else:
        raise ValueError(f"Unknown predicate: {original_predicate}")


# General function to read an .obo ontontolgy file into memory using pronto to gather all terms that do not fall under a particular parent class
def read_ontology_to_exclusion_terms(ontology_obo_file, umbrella_term="HP:0000118", include=False):
    
    # Read ontology file into memory
    onto = Ontology(ontology_obo_file)
    exclude_terms = {}
    term_count = len(list(onto.terms()))
    
    for term in onto.terms():
        
        # Gather ancestor terms and update our filtering datastructure accordingly
        parent_terms = {ancestor.id: ancestor.name for ancestor in term.superclasses()}
        if include == False:
            if umbrella_term not in parent_terms:
                exclude_terms.update({term.id:term.name})

        elif include == True:
            if umbrella_term in parent_terms:
                exclude_terms.update({term.id:term.name})
    
    print("- Terms from ontology found that do not belong to parent class {} {}/{}".format(umbrella_term,
                                                                                           format(len(exclude_terms)), 
                                                                                           format(term_count)))
    return exclude_terms


# This is depricated... We now use pronto + hp.obo file to pull these terms in dynamically 
# from hp ontology using the read_ontology_to_exclusion_terms function above
# # HPO "Mode of Inheritance" terms - https://www.ebi.ac.uk/ols4/ontologies/hp
# hpo_to_mode_of_inheritance: Dict = {"HP:0001417": "X-linked inheritance",
#                                     "HP:0000005": "Mode of inheritance",
#                                     "HP:0001423": "X-linked dominant inheritance",
#                                     "HP:0010982": "Polygenic inheritance",
#                                     "HP:0010984": "Digenic inheritance",
#                                     "HP:0001450": "Y-linked inheritance",
#                                     "HP:0001475": "Male-limited autosomal dominant",
#                                     "HP:0032384": "Uniparental isodisomy",
#                                     "HP:0001426": "Multifactorial inheritance",
#                                     "HP:0000006": "Autosomal dominant inheritance",
#                                     "HP:0032113": "Semidominant inheritance",
#                                     "HP:0032382": "Uniparental disomy",
#                                     "HP:0032383": "Uniparental heterodisomy",
#                                     "HP:0001452": "Autosomal dominant contiguous gene syndrome",
#                                     "HP:0003745": "Sporadic",
#                                     "HP:0001425": "Heterogeneous",
#                                     "HP:0001466": "Contiguous gene syndrome",
#                                     "HP:0003744": "Genetic anticipation with paternal anticipation bias",
#                                     "HP:0012274": "Autosomal dominant inheritance with paternal imprinting",
#                                     "HP:0000007": "Autosomal recessive inheritance",
#                                     "HP:0003743": "Genetic anticipation",
#                                     "HP:0001419": "X-linked recessive inheritance",
#                                     "HP:0001442": "Somatic mosaicism",
#                                     "HP:0001428": "Somatic mutation",
#                                     "HP:0010983": "Oligogenic inheritance",
#                                     "HP:0001444": "Autosomal dominant somatic cell mutation",
#                                     "HP:0031362": "Sex-limited autosomal recessive inheritance",
#                                     "HP:0025352": "Autosomal dominant germline de novo mutation",
#                                     "HP:0001470": "Sex-limited autosomal dominant",
#                                     "HP:0012275": "Autosomal dominant inheritance with maternal imprinting",
#                                     "HP:0001427": "Mitochondrial inheritance",
#                                     "HP:0010985": "Gonosomal inheritance"}
