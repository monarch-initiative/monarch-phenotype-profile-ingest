# monarch-phenotype-profile-ingest Report

{{ get_nodes_report() }}

{{ get_edges_report() }}

# Human Phenotype Ontology Annotations (HPOA)

The [Human Phenotype Ontology](http://human-phenotype-ontology.org) group
curates and assembles over 115,000 annotations to hereditary diseases
using the HPO ontology. Here we create Biolink associations
between diseases and phenotypic features, together with their evidence,
and age of onset and frequency (if known).

There are four HPOA ingests - 'disease-to-phenotype', 'disease-to-mode-of-inheritance', 'gene-to-disease' and 'gene-to-phenotype' - that parse out records from the [HPO Annotation File](http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa).

## [Disease to Phenotype](#disease_to_phenotype)

This ingest processes the tab-delimited [phenotype.hpoa](https://hpo-annotation-qc.readthedocs.io/en/latest/annotationFormat.html#phenotype-hpoa-format) file, filtered for rows with **Aspect == 'P'** (phenotypic anomalies).

### Biolink Entities Captured

* biolink:DiseaseToPhenotypicFeatureAssociation
    * id (random uuid)
    * subject (disease.id)
    * predicate (has_phenotype)
    * negated (True if 'qualifier' == "NOT")
    * object (phenotypicFeature.id)
    * publications (List[publication.id])
    * has_evidence (List[evidence.id])
    * sex_qualifier (female -> PATO:0000383, male -> PATO:0000384 or None)
    * onset_qualifier (Onset.id)
    * frequency_qualifier (See Frequencies section in hpoa.md)
    * aggregating_knowledge_source (["infores:monarchinitiative"])
    * primary_knowledge_source ("infores:hpo-annotations")

### Example Source Data

```json
{
  "database_id": "OMIM:117650",
  "disease_name": "Cerebrocostomandibular syndrome",
  "qualifier": "",
  "hpo_id": "HP:0001249",
  "reference": "OMIM:117650",
  "evidence": "TAS",
  "onset": "",
  "frequency": "50%",
  "sex": "",
  "modifier": "",
  "aspect": "P"
}
```

### Example Transformed Data

```json
{
  "id": "uuid:...",
  "subject": "OMIM:117650",
  "predicate": "biolink:has_phenotype",
  "object": "HP:0001249",
  "frequency_qualifier": 50.0,
  "has_evidence": ["ECO:0000033"],
  "primary_knowledge_source": "infores:hpo-annotations",
  "aggregator_knowledge_source": ["infores:monarchinitiative"]
}
```

## [Disease to Mode of Inheritance](#disease_modes_of_inheritance)

This ingest processes the tab-delimited [phenotype.hpoa](https://hpo-annotation-qc.readthedocs.io/en/latest/annotationFormat.html#phenotype-hpoa-format) file, filtered for rows with **Aspect == 'I'** (inheritance).

### Biolink Entities Captured

* biolink:DiseaseOrPhenotypicFeatureToGeneticInheritanceAssociation
    * id (random uuid)
    * subject (disease.id)
    * predicate (has_mode_of_inheritance)
    * object (geneticInheritance.id)
    * publications (List[publication.id])
    * has_evidence (List[evidence.id])
    * aggregating_knowledge_source (["infores:monarchinitiative"])
    * primary_knowledge_source ("infores:hpo-annotations")

### Example Source Data

```json
{
  "database_id": "OMIM:300425",
  "disease_name": "Autism susceptibility, X-linked 1",
  "qualifier": "",
  "hpo_id": "HP:0001417",
  "reference": "OMIM:300425",
  "evidence": "IEA",
  "aspect": "I"
}
```

### Example Transformed Data

```json
{
  "id": "uuid:...",
  "subject": "OMIM:300425",
  "predicate": "biolink:has_mode_of_inheritance",
  "object": "HP:0001417",
  "has_evidence": ["ECO:0000501"],
  "primary_knowledge_source": "infores:hpo-annotations",
  "aggregator_knowledge_source": ["infores:monarchinitiative"]
}
```

## [Gene to Disease](#gene_to_disease)

This ingest replaces the direct OMIM ingest so that we share gene-to-disease associations 1:1 with HPO. It processes the tab-delimited [genes_to_disease.txt](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_disease.txt) file.

### Biolink Entities Captured

* biolink:CorrelatedGeneToDiseaseAssociation or biolink:CausalGeneToDiseaseAssociation (depending on predicate)
    * id (random uuid)
    * subject (ncbi_gene_id)
    * predicate (association_type)
      * MENDELIAN: `biolink:causes`
      * POLYGENIC: `biolink:contributes_to`
      * UNKNOWN: `biolink:gene_associated_with_condition`
    * object (disease_id)
    * primary_knowledge_source (source)
      * medgen: `infores:omim`
      * orphanet: `infores:orphanet`
    * aggregator_knowledge_source (["infores:monarchinitiative"])
      * also for medgen: `infores:medgen`

### Example Source Data

```json
{
  "association_type": "MENDELIAN",
  "disease_id": "OMIM:212050",
  "gene_symbol": "CARD9",
  "ncbi_gene_id": "NCBIGene:64170",
  "source": "ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen"
}
```

### Example Transformed Data

```json
{
  "id": "uuid:...",
  "subject": "NCBIGene:64170",
  "predicate": "biolink:causes",
  "object": "OMIM:212050",
  "primary_knowledge_source": "infores:omim",
  "aggregator_knowledge_source": ["infores:monarchinitiative", "infores:medgen"]
}
```

## [Gene to Phenotype](#gene_to_phenotype)

This ingest processes the tab-delimited [genes_to_phenotype_preprocessed.tsv](http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt) file, which is generated by joining genes_to_phenotype.txt with both phenotype.hpoa (for publications) and genes_to_disease.txt (for association types).

The data is pre-processed using the `scripts/gene_to_phenotype_extras.py` script, which performs joins to add both publication information and gene-to-disease association types. The ingest then filters to only include associations where the gene-to-disease relationship is MENDELIAN (including mixed inheritance patterns like "MENDELIAN;POLYGENIC"). This filtering reduces the dataset from ~312K to ~141K associations, focusing on high-confidence gene-phenotype relationships.

### Biolink Entities Captured

* biolink:GeneToPhenotypicFeatureAssociation
    * id (random uuid)
    * subject (gene.id)
    * predicate (has_phenotype)
    * object (phenotypicFeature.id)
    * publications (List[publication.id])
    * frequency_qualifier (calculated from frequency data if available)
    * in_taxon (NCBITaxon:9606)
    * aggregating_knowledge_source (["infores:monarchinitiative"])
    * primary_knowledge_source ("infores:hpo-annotations")

### Example Source Data

```json
{
  "ncbi_gene_id": "8192",
  "gene_symbol": "CLPP",
  "hpo_id": "HP:0000252",
  "hpo_name": "Microcephaly",
  "publications": "PMID:1234567;OMIM:614129",
  "frequency": "3/10",
  "disease_id": "OMIM:614129",
  "gene_to_disease_association_types": "MENDELIAN"
}
```

### Example Transformed Data

```json
{
  "id": "uuid:...",
  "subject": "NCBIGene:8192",
  "predicate": "biolink:has_phenotype",
  "object": "HP:0000252",
  "publications": ["PMID:1234567","OMIM:614129"],
  "frequency_qualifier": 30.0,
  "in_taxon": "NCBITaxon:9606",
  "primary_knowledge_source": "infores:hpo-annotations",
  "aggregator_knowledge_source": ["infores:monarchinitiative"]
}
```

## Citation

Sebastian Köhler, Michael Gargano, Nicolas Matentzoglu, Leigh C Carmody, David Lewis-Smith, Nicole A Vasilevsky, Daniel Danis, Ganna Balagura, Gareth Baynam, Amy M Brower, Tiffany J Callahan, Christopher G Chute, Johanna L Est, Peter D Galer, Shiva Ganesan, Matthias Griese, Matthias Haimel, Julia Pazmandi, Marc Hanauer, Nomi L Harris, Michael J Hartnett, Maximilian Hastreiter, Fabian Hauck, Yongqun He, Tim Jeske, Hugh Kearney, Gerhard Kindle, Christoph Klein, Katrin Knoflach, Roland Krause, David Lagorce, Julie A McMurry, Jillian A Miller, Monica C Munoz-Torres, Rebecca L Peters, Christina K Rapp, Ana M Rath, Shahmir A Rind, Avi Z Rosenberg, Michael M Segal, Markus G Seidel, Damian Smedley, Tomer Talmy, Yarlalu Thomas, Samuel A Wiafe, Julie Xian, Zafer Yüksel, Ingo Helbig, Christopher J Mungall, Melissa A Haendel, Peter N Robinson, The Human Phenotype Ontology in 2021, Nucleic Acids Research, Volume 49, Issue D1, 8 January 2021, Pages D1207–D1217, https://doi.org/10.1093/nar/gkaa1043