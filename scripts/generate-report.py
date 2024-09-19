from pathlib import Path
import os
import duckdb


# Grab edge filepaths and generate a report for each one via duckdb
edge_files = [str(fpath) for fpath in Path("./output").iterdir() if str(fpath).endswith("_edges.tsv")]

# Write individual report files
for efile in edge_files:
    query = f"""
    SELECT category, split_part(subject, ':', 1) as subject_prefix, predicate,
    split_part(object, ':', 1) as object_prefix, count(*)
    FROM '{efile}'
    GROUP BY all
    ORDER BY all
    """

    rep_fpath = "{}_edges_report.tsv".format(efile.split('_edges')[0])
    sql_cmd = f"""copy ({query}) to '{rep_fpath}' (header, delimiter '\t')"""
    duckdb.sql(sql_cmd)

# Grab each report and combine into larger report
edge_rep_files = [str(fpath) for fpath in Path("./output").iterdir() 
                  if str(fpath).endswith("_edges_report.tsv")]

union_query = " UNION ALL ".join(["SELECT *, '{}' AS filename FROM '{}'".format(Path(fpath).stem, fpath) for fpath in edge_rep_files])
sql_cmd = "copy ({}) to '{}' (header, delimiter '\t')".format(union_query, "docs/edges_report.tsv")
duckdb.sql(sql_cmd)