import argparse
import csv
from collections import defaultdict

import yaml

COLUMNS = ["qseqid", "sseqid", "pident", "length", "qcovs", "evalue", "bitscore"]


def read_hits(path):
    hits = defaultdict(list)
    for line in open(path):
        row = dict(zip(COLUMNS, line.rstrip("\n").split("\t")))
        row["pident"] = float(row["pident"])
        row["qcovs"] = float(row["qcovs"])
        row["bitscore"] = float(row["bitscore"])
        row["species"] = row["sseqid"].split("|")[1].replace("_", " ")
        row["genus"] = row["species"].split(" ")[0]
        hits[row["qseqid"]].append(row)
    return hits


def best_per_species(rows):
    best = {}
    for r in rows:
        if r["species"] not in best or r["bitscore"] > best[r["species"]]["bitscore"]:
            best[r["species"]] = r
    return sorted(best.values(), key=lambda r: -r["bitscore"])


def assign(rows, thresholds):
    ranked = best_per_species(rows)
    top = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    margin = top["pident"] - second["pident"] if second else 100.0
    result = {"top_species": top["species"], "top_identity": top["pident"], "top_coverage": top["qcovs"],
              "second_species": second["species"] if second else "", "margin": round(margin, 2)}
    if top["qcovs"] < thresholds["min_query_coverage"]:
        result["assigned"] = "unassigned"
        result["rank"] = "none"
        result["reason"] = "low coverage"
    elif top["pident"] < thresholds["min_identity"]:
        result["assigned"] = top["genus"] if top["pident"] >= thresholds["min_identity_genus"] else "unassigned"
        result["rank"] = "genus" if result["assigned"] != "unassigned" else "none"
        result["reason"] = "identity below species threshold"
    elif margin < thresholds["min_margin_to_second"]:
        same_genus = all(r["genus"] == top["genus"] for r in ranked
                         if top["pident"] - r["pident"] < thresholds["min_margin_to_second"])
        result["assigned"] = top["genus"] if same_genus else "unassigned"
        result["rank"] = "genus" if same_genus else "none"
        result["reason"] = "second species too close"
    else:
        result["assigned"] = top["species"]
        result["rank"] = "species"
        result["reason"] = "pass"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("hits")
    parser.add_argument("out")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--min-identity", type=float)
    parser.add_argument("--min-margin", type=float)
    args = parser.parse_args()

    thresholds = dict(yaml.safe_load(open(args.config))["thresholds"])
    if args.min_identity is not None:
        thresholds["min_identity"] = args.min_identity
    if args.min_margin is not None:
        thresholds["min_margin_to_second"] = args.min_margin

    hits = read_hits(args.hits)
    fields = ["query", "assigned", "rank", "reason", "top_species", "top_identity", "top_coverage",
              "second_species", "margin"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for query, rows in hits.items():
            writer.writerow({"query": query} | assign(rows, thresholds))


if __name__ == "__main__":
    main()
