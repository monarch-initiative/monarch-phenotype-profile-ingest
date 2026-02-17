# Phenotype Profiles

This ingest aggregates phenotype profile data from curated sources. Currently it includes data from the Human Phenotype Ontology Annotations (HPOA).

## HPOA

The [Human Phenotype Ontology](http://human-phenotype-ontology.org) group curates and assembles over 115,000 annotations to hereditary diseases using the HPO ontology. This ingest transforms HPOA data into gene-phenotype, disease-phenotype, gene-disease, and disease-inheritance associations.

### Data Sources

- [HPOA genes_to_phenotype.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt)
- [HPOA genes_to_disease.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_disease.txt)
- [HPOA phenotype.hpoa](http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa)
- [Mondo SSSOM mappings](https://data.monarchinitiative.org/mappings/latest/mondo.sssom.tsv) (for disease ID normalization)
- [HP ontology](http://purl.obolibrary.org/obo/hp.obo) (for inheritance term validation)

### Gene to Phenotype

Gene-to-phenotype associations derived from HPOA, with disease context preserved. A preprocessing step joins the genes_to_phenotype file with disease mappings and Mondo SSSOM to normalize disease IDs to MONDO where possible (`ORPHA:` prefixes are also normalized to `Orphanet:` for SSSOM compatibility).

Frequency data is captured in multiple forms: as HPO frequency qualifier terms (HP:0040280-HP:0040285), as percentages, or as counts/totals from cohort data.

**Biolink Captured:**

- `biolink:GeneToPhenotypicFeatureAssociation`
    - id (UUID)
    - subject (`NCBIGene:{id}`)
    - predicate (`biolink:has_phenotype`)
    - object (HPO term ID)
    - disease_context_qualifier (MONDO or original disease ID)
    - frequency_qualifier (HPO frequency term, when available)
    - has_percentage (percentage, when available)
    - has_quotient (quotient, when available)
    - has_count (numerator from cohort ratio, when available)
    - has_total (denominator from cohort ratio, when available)
    - publications
    - primary_knowledge_source (`infores:hpo-annotations`)
    - aggregator_knowledge_source (`["infores:monarchinitiative"]`)
    - knowledge_level (`logical_entailment`)
    - agent_type (`automated_agent`)

### Disease to Phenotype

Disease-to-phenotype associations from the phenotype.hpoa file, filtered to only "P" (phenotypic anomaly) aspect records. Includes rich annotation data: evidence codes, sex qualifiers, onset, and frequency information.

The primary knowledge source is determined by the disease ID prefix: OMIM diseases use `infores:omim`, Orphanet diseases use `infores:orphanet`, and DECIPHER diseases use `infores:decipher`.

**Biolink Captured:**

- `biolink:DiseaseToPhenotypicFeatureAssociation`
    - id (UUID)
    - subject (disease ID, with `ORPHA:` normalized to `Orphanet:`)
    - predicate (`biolink:has_phenotype`)
    - negated (true when qualifier is "NOT")
    - object (HPO term ID)
    - has_evidence (ECO term mapped from 3-letter evidence code)
    - sex_qualifier (PATO term: `PATO:0000383` female, `PATO:0000384` male)
    - onset_qualifier (HPO onset term, when available)
    - frequency_qualifier (HPO frequency term, when available)
    - has_percentage, has_quotient, has_count, has_total (frequency data)
    - publications
    - primary_knowledge_source (determined by disease prefix)
    - aggregator_knowledge_source (`["infores:monarchinitiative", "infores:hpo-annotations"]`)
    - knowledge_level (`knowledge_assertion`)
    - agent_type (`manual_agent`)

#### Evidence Code Mapping

| HPOA Code | ECO Term | Label |
|---|---|---|
| IEA | ECO:0000501 | inferred from electronic annotation |
| PCS | ECO:0006017 | published clinical study evidence |
| TAS | ECO:0000304 | traceable author statement |
| ICE | ECO:0006019 | individual clinical experience evidence |

### Gene to Disease

Gene-to-disease associations from the HPOA genes_to_disease file. The association type determines the Biolink class and predicate:

| Association Type | Biolink Class | Predicate |
|---|---|---|
| MENDELIAN | `CausalGeneToDiseaseAssociation` | `biolink:causes` |
| POLYGENIC | `CorrelatedGeneToDiseaseAssociation` | `biolink:contributes_to` |
| UNKNOWN | `CorrelatedGeneToDiseaseAssociation` | `biolink:gene_associated_with_condition` |

The primary knowledge source is derived from the source column: `medgen` sources map to `infores:omim` (with `infores:medgen` as additional aggregator), `orphadata` sources map to `infores:orphanet`.

**Biolink Captured:**

- `biolink:CausalGeneToDiseaseAssociation` / `biolink:CorrelatedGeneToDiseaseAssociation`
    - id (UUID)
    - subject (NCBIGene ID)
    - predicate (mapped from association type, see above)
    - object (disease ID, with `ORPHA:` normalized to `Orphanet:`)
    - primary_knowledge_source (derived from source column)
    - aggregator_knowledge_source (includes `infores:monarchinitiative`)
    - knowledge_level (`knowledge_assertion`)
    - agent_type (`manual_agent`)

### Disease Mode of Inheritance

Disease-to-inheritance associations from the phenotype.hpoa file, filtered to "I" (inheritance) aspect records. Only rows where the HPO term is a descendant of "Mode of inheritance" (HP:0000005) in the HP ontology are included.

**Biolink Captured:**

- `biolink:DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation`
    - id (UUID)
    - subject (disease ID)
    - predicate (`biolink:has_mode_of_inheritance`)
    - object (HPO inheritance term ID)
    - has_evidence (ECO term mapped from evidence code)
    - publications
    - primary_knowledge_source (`infores:hpo-annotations`)
    - aggregator_knowledge_source (`["infores:monarchinitiative"]`)
    - knowledge_level (`knowledge_assertion`)
    - agent_type (`manual_agent`)

### HPOA Citation

Kohler S, Gargano M, Matentzoglu N, Carmody LC, Lewis-Smith D, Vasilevsky NA, Danis D, et al. The Human Phenotype Ontology in 2024: Phenotype-Based Knowledge for Rare Disease Discovery. Nucleic Acids Research. 2024;52(D1):D1333-D1346. doi: 10.1093/nar/gkad1005. PMID: 37953324

## License

BSD-3-Clause
