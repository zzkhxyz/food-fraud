import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def asv_sizes(path):
    sizes = {}
    for line in open(path):
        if line.startswith(">"):
            name = line[1:].strip()
            size = int(re.search(r"size=(\d+)", name).group(1))
            sizes[name] = size
    return sizes


def merge_stats(path):
    text = open(path).read()
    merged = re.search(r"(\d+)\s+Pairs merged", text)
    total = re.search(r"(\d+)\s+Pairs", text)
    return int(merged.group(1)) if merged else 0, int(total.group(1)) if total else 0


def composition(run, assign_path, asv_path):
    sizes = asv_sizes(asv_path)
    counts = defaultdict(int)
    for row in csv.DictReader(open(assign_path), delimiter="\t"):
        counts[(row["assigned"], row["rank"])] += sizes.get(row["query"], 0)
    total = sum(counts.values())
    rows = []
    for (taxon, rank), n in sorted(counts.items(), key=lambda x: -x[1]):
        rows.append({"run": run, "taxon": taxon, "rank": rank, "reads": n,
                     "fraction": round(n / total, 4) if total else 0})
    return rows


def verdict(declared, declared_rank, found):
    if declared_rank == "none":
        return "label not specific" if found else "no identification"
    if declared_rank == "species":
        return "label confirmed" if declared in found else "label not confirmed"
    genus_found = {t.split(" ")[0] for t in found}
    return "label confirmed" if declared in genus_found else "label not confirmed"


def main():
    runs_tsv, labels_tsv, results, out_comp, out_label, out_qc = sys.argv[1:7]
    results = Path(results)
    runs = {r["run_accession"]: r for r in csv.DictReader(open(runs_tsv), delimiter="\t")}
    labels = {r["library_name"]: r for r in csv.DictReader(open(labels_tsv), delimiter="\t")}

    comp_rows, label_rows, qc_rows = [], [], []
    for run in sorted(runs):
        assign_path = results / "assign" / f"{run}.tsv"
        if not assign_path.exists():
            continue
        rows = composition(run, assign_path, results / "asv" / f"{run}.asv.fasta")
        comp_rows.extend(rows)

        fastp = json.load(open(results / "qc" / f"{run}.fastp.json"))
        merged, total_pairs = merge_stats(results / "merged" / f"{run}.merge.log")
        qc_rows.append({"run": run, "library": runs[run]["library_name"],
                        "raw_reads": fastp["summary"]["before_filtering"]["total_reads"],
                        "after_fastp": fastp["summary"]["after_filtering"]["total_reads"],
                        "q30_rate_before": round(fastp["summary"]["before_filtering"]["q30_rate"], 3),
                        "q30_rate_after": round(fastp["summary"]["after_filtering"]["q30_rate"], 3),
                        "pairs_merged": merged, "merge_rate": round(merged / total_pairs, 3) if total_pairs else 0,
                        "asv_count": len(asv_sizes(results / "asv" / f"{run}.asv.fasta"))})

        label = labels.get(runs[run]["library_name"], {})
        species_found = [r["taxon"] for r in rows if r["rank"] == "species" and r["fraction"] >= 0.01]
        genus_found = [r["taxon"] for r in rows if r["rank"] == "genus" and r["fraction"] >= 0.01]
        main_taxon = rows[0]["taxon"] if rows else ""
        label_rows.append({"run": run, "product": label.get("product", runs[run]["library_name"]),
                           "declared": label.get("declared_taxon", ""), "expectation": label.get("expectation", ""),
                           "main_taxon": main_taxon, "main_fraction": rows[0]["fraction"] if rows else 0,
                           "species_found": "; ".join(species_found), "genus_only": "; ".join(genus_found),
                           "unassigned_fraction": sum(r["fraction"] for r in rows if r["taxon"] == "unassigned"),
                           "verdict": verdict(label.get("declared_taxon", ""), label.get("declared_rank", "none"),
                                              species_found + genus_found)})

    for path, rows in [(out_comp, comp_rows), (out_label, label_rows), (out_qc, qc_rows)]:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
