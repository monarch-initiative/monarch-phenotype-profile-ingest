# Phenotype Profiles

This ingest aggregates phenotype profile data from curated sources. Currently it includes data from the Human Phenotype Ontology Annotations (HPOA) and Orphanet gene-disease associations (Orphanet product 6).

## HPOA

The [Human Phenotype Ontology](http://human-phenotype-ontology.org) group curates and assembles over 115,000 annotations to hereditary diseases using the HPO ontology. This ingest transforms HPOA data into gene-phenotype, disease-phenotype, gene-disease, and disease-inheritance associations.

### Data Sources

- [HPOA genes_to_phenotype.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt)
- [HPOA genes_to_disease.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_disease.txt) (OMIM association types for the gene-to-phenotype preprocess)
- [Orphanet product 6, en_product6.xml](https://www.orphadata.com/data/xml/en_product6.xml) (genes associated with rare diseases, CC BY 4.0)
- [HGNC complete set](http://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt) (to resolve Orphanet genes to NCBIGene ids)
- [HPOA phenotype.hpoa](http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa)
- [Mondo SSSOM mappings](https://data.monarchinitiative.org/mappings/latest/mondo.sssom.tsv) (for disease ID normalization)
- [HP ontology](http://purl.obolibrary.org/obo/hp.obo) (for inheritance term validation)

### Gene to Phenotype

Gene-to-phenotype associations derived from HPOA, with disease context preserved. A preprocessing step joins the genes_to_phenotype file with disease mappings and Mondo SSSOM to normalize disease IDs to MONDO where possible (`ORPHA:` prefixes are also normalized to `Orphanet:` for SSSOM compatibility).

Only rows whose gene-to-disease association is MENDELIAN are kept, since HPOA's `genes_to_phenotype.txt` itself applies no type filter (it includes candidate genes, biomarkers and somatic associations). For OMIM diseases the association type comes from HPOA's `genes_to_disease.txt`; for Orphanet diseases, where HPOA reports every row as `UNKNOWN`, it comes from Orphanet product 6 (see [Orphanet Gene to Disease](#orphanet-gene-to-disease)): *Disease-causing germline mutation(s)* (plain, loss of function or gain of function) with status *Assessed*.

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

### Orphanet Gene to Disease

Gene-to-disease associations read directly from Orphanet product 6 (`en_product6.xml`). HPOA's `genes_to_disease.txt` collapses every Orphanet row to `association_type = UNKNOWN`, so until this transform existed no Orphanet-curated gene-disease association could be causal in Monarch, and none could feed gene-to-phenotype inference ([monarch-app#1488](https://github.com/monarch-initiative/monarch-app/issues/1488)). OMIM gene-to-disease associations are produced by [omim-ingest](https://github.com/monarch-initiative/omim-ingest), not here.

A preprocessing step (`scripts/orphanet_gene_to_disease_extras.py`) flattens the XML to `data/orphanet_gene_to_disease.tsv`, resolving each gene to an NCBIGene id through the HGNC complete set (by HGNC id, falling back to symbol). Genes that cannot be resolved (withdrawn HGNC locus entries such as SPG34, snoRNA clusters such as SNORD116@) are counted and skipped.

The Orphanet `DisorderGeneAssociationType` and `DisorderGeneAssociationStatus` determine the Biolink class and predicate:

| Orphanet association type | Status | Biolink Class | Predicate | Notes |
|---|---|---|---|---|
| Disease-causing germline mutation(s) in | Assessed | `CausalGeneToDiseaseAssociation` | `biolink:causes` | feeds g2p inference |
| Disease-causing germline mutation(s) (loss of function) in | Assessed | `CausalGeneToDiseaseAssociation` | `biolink:causes` | `subject_form_or_variant_qualifier = loss_of_function_variant_form`; feeds g2p inference |
| Disease-causing germline mutation(s) (gain of function) in | Assessed | `CausalGeneToDiseaseAssociation` | `biolink:causes` | `subject_form_or_variant_qualifier = gain_of_function_variant_form`; feeds g2p inference |
| Disease-causing somatic mutation(s) in | Assessed | `CausalGeneToDiseaseAssociation` | `biolink:causes` | not treated as Mendelian: does not feed g2p inference |
| Major susceptibility factor in | Assessed | `CorrelatedGeneToDiseaseAssociation` | `biolink:contributes_to` | |
| Modifying germline mutation in | Assessed | `CorrelatedGeneToDiseaseAssociation` | `biolink:contributes_to` | |
| Candidate gene tested in | any | `CorrelatedGeneToDiseaseAssociation` | `biolink:gene_associated_with_condition` | |
| Biomarker tested in | any | `CorrelatedGeneToDiseaseAssociation` | `biolink:gene_associated_with_condition` | |
| Part of a fusion gene in | any | `CorrelatedGeneToDiseaseAssociation` | `biolink:gene_associated_with_condition` | |
| Role in the phenotype of | any | `CorrelatedGeneToDiseaseAssociation` | `biolink:gene_associated_with_condition` | chromosomal-syndrome case (e.g. 22q11.2 deletion / TBX1); never causal |
| any type | Not yet assessed | `CorrelatedGeneToDiseaseAssociation` | `biolink:gene_associated_with_condition` | |

The original Orphanet association type is kept verbatim in `original_predicate`, the status in `qualifiers`, and the HGNC id in `original_subject`. `SourceOfValidation` PMIDs become `publications`. Orphanet's product 9 inheritance is not used: inheritance is per disorder, not per gene, so multi-valued lists cannot be resolved to a gene.

**Biolink Captured:**

- `biolink:CausalGeneToDiseaseAssociation` / `biolink:CorrelatedGeneToDiseaseAssociation`
    - id
    - subject (`NCBIGene:{id}`, resolved via HGNC)
    - predicate (mapped from association type and status, see above)
    - object (`Orphanet:{OrphaCode}`)
    - original_subject (`HGNC:{id}`)
    - original_predicate (Orphanet `DisorderGeneAssociationType` label)
    - qualifiers (Orphanet `DisorderGeneAssociationStatus`: `Assessed` or `Not yet assessed`)
    - subject_form_or_variant_qualifier (loss/gain of function, causal associations only)
    - publications (PMIDs from `SourceOfValidation`)
    - primary_knowledge_source (`infores:orphanet`)
    - aggregator_knowledge_source (`["infores:monarchinitiative"]`)
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

### Orphanet Citation

Orphanet: an online database of rare diseases and orphan drugs. Copyright, INSERM 1997. Available at https://www.orpha.net. Data: Orphadata, https://www.orphadata.com, licensed under CC BY 4.0.

### HPOA Citation

Kohler S, Gargano M, Matentzoglu N, Carmody LC, Lewis-Smith D, Vasilevsky NA, Danis D, et al. The Human Phenotype Ontology in 2024: Phenotype-Based Knowledge for Rare Disease Discovery. Nucleic Acids Research. 2024;52(D1):D1333-D1346. doi: 10.1093/nar/gkad1005. PMID: 37953324

## License

BSD-3-Clause
