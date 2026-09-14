import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

results = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("web/data.json")

markers = {"COI", "16S", "12S", "CYTB"}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


reference = []
for row in read(results / "reference" / "reference_stats.tsv"):
    if row["marker"] in markers:
        reference.append({
            "marker": row["marker"],
            "sequences": int(row["sequences"]),
            "species": int(row["species"]),
        })

illumina = []
for row in read(results / "illumina" / "label_vs_content.tsv"):
    illumina.append({
        "run": row["run"],
        "product": row["product"],
        "declared": row["declared"],
        "expectation": row["expectation"],
        "main_taxon": row["main_taxon"],
        "main_fraction": float(row["main_fraction"]),
        "unassigned_fraction": float(row["unassigned_fraction"]),
        "verdict": row["verdict"],
    })

composition = defaultdict(list)
for row in read(results / "illumina" / "composition.tsv"):
    composition[row["run"]].append({
        "taxon": row["taxon"],
        "rank": row["rank"],
        "fraction": float(row["fraction"]),
    })
composition = {run: sorted(items, key=lambda x: x["fraction"], reverse=True)[:6]
               for run, items in composition.items()}

nanopore = []
summary = defaultdict(int)
for row in read(results / "nanopore" / "validation.tsv"):
    nanopore.append({
        "sample": row["sample"],
        "truth": row["truth"],
        "call": row["call"],
        "result": row["result"],
    })
    summary[row["result"]] += 1

sensitivity = []
for row in read(results / "nanopore" / "sensitivity.tsv"):
    sensitivity.append({
        "identity": int(row["min_identity"]),
        "margin": int(row["min_margin"]),
        "false_id_rate": float(row["false_id_rate"]),
    })

mock = []
for row in read(results / "mock" / "mock_eval.tsv"):
    mock.append({
        "sample": row["sample"],
        "expected": row["expected"],
        "detected": row["detected"],
        "reads": int(row["reads"]),
        "false_read_fraction": float(row["false_read_fraction"]),
    })

data = {
    "reference": reference,
    "illumina": illumina,
    "composition": composition,
    "nanopore": nanopore,
    "nanopore_summary": dict(summary),
    "sensitivity": sensitivity,
    "mock": mock,
}

out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    json.dump(data, f, indent=2)

print("wrote", out)
