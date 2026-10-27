import duckdb

db = duckdb.connect(":memory:", read_only=False)
db.execute("""
copy (
with
  hpoa as (select * from read_csv('data/phenotype.hpoa')),
  g2p as (select * from read_csv('data/genes_to_phenotype.txt')),
  -- OMIM gene-to-disease types come from HPOA (mim2gene_medgen); Orphanet rows in
  -- genes_to_disease.txt are all UNKNOWN, so Orphanet types come from product 6
  -- (data/orphanet_gene_to_disease.tsv, written by scripts/orphanet_gene_to_disease_extras.py).
  -- Only MENDELIAN feeds g2p (see gene_to_phenotype_transform.yaml); the Orphanet
  -- SOMATIC / POLYGENIC / UNKNOWN codes are carried through but filtered out there.
  hpoa_g2d as (select
    replace(ncbi_gene_id, 'NCBIGene:', '') as ncbi_gene_id_clean,
    disease_id,
    association_type
    from read_csv('data/genes_to_disease.txt')
    where source not like '%orphadata%'),
  orphanet_g2d as (select
    replace(ncbi_gene_id, 'NCBIGene:', '') as ncbi_gene_id_clean,
    replace(disease_id, 'Orphanet:', 'ORPHA:') as disease_id,
    association_type_code as association_type
    from read_csv('data/orphanet_gene_to_disease.tsv', all_varchar = true)
    where ncbi_gene_id is not null and ncbi_gene_id <> ''),
  g2d as (select * from hpoa_g2d union all select * from orphanet_g2d),
  g2d_grouped as (select 
    ncbi_gene_id_clean,
    disease_id,
    array_to_string(list(distinct association_type), ';') as association_types
    from g2d 
    group by ncbi_gene_id_clean, disease_id)
select g2p.*, 
       array_to_string(list(hpoa.reference),';') as publications,
       coalesce(g2d_grouped.association_types, '') as gene_to_disease_association_types
from g2p
     left outer join hpoa on hpoa.hpo_id = g2p.hpo_id
                 and g2p.disease_id = hpoa.database_id
		             and hpoa.frequency = g2p.frequency
     left outer join g2d_grouped on g2p.ncbi_gene_id = g2d_grouped.ncbi_gene_id_clean
                 and g2p.disease_id = g2d_grouped.disease_id
group by all
) to 'data/genes_to_phenotype_preprocessed.tsv' (delimiter '\t', header true)
""")
