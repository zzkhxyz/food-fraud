import csv
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from identify import assign, read_hits


def truth_species(sample_title):
    match = re.search(r"from (\w+ \w+)", sample_title)
    return match.group(1) if match else ""


def sample_call(assignments):
    counts = Counter(a["assigned"] for a in assignments if a["assigned"] != "unassigned")
    total = len(assignments)
    if not counts:
        return "unassigned", 0.0
    taxon, n = counts.most_common(1)[0]
    return taxon, n / total


def compare(truth, call):
    if call == "unassigned":
        return "no call"
    if call == truth:
        return "correct species"
    if " " not in call and call == truth.split(" ")[0]:
        return "correct genus"
    if truth.split(" ")[1] in ("sp", "sp.") and call.split(" ")[0] == truth.split(" ")[0]:
        return "correct genus"
    return "wrong"


def read_stats(path):
    stats = {}
    for line in open(path):
        cols = line.rstrip("\n").split("\t")
        if len(cols) > 5:
            stats[cols[0]] = {"reads": cols[1], "bases": cols[2], "n50": cols[3], "longest": cols[4],
                              "shortest": cols[5], "mean_length": cols[6], "median_length": cols[7],
                              "mean_quality": cols[8], "median_quality": cols[9]}
    return stats


def main():
    runs_tsv, result_dir, out_validation, out_sensitivity, out_qc = sys.argv[1:6]
    config = yaml.safe_load(open("config.yaml"))
    base = dict(config["thresholds"])
    runs = {r["run_accession"]: r for r in csv.DictReader(open(runs_tsv), delimiter="\t")}

    validation, qc = [], []
    hits_by_run = {}
    for run in sorted(runs):
        hits_path = Path(result_dir) / "assign" / f"{run}.tsv.hits"
        if not hits_path.exists():
            continue
        hits_by_run[run] = read_hits(hits_path)
        truth = truth_species(runs[run]["sample_title"])
        assignments = [assign(rows, base) for rows in hits_by_run[run].values()]
        call, support = sample_call(assignments)
        ranks = Counter(a["rank"] for a in assignments)
        validation.append({"run": run, "sample": runs[run]["sample_alias"], "truth": truth, "call": call,
                           "support": round(support, 3), "reads_assigned": len(assignments),
                           "species_level": ranks.get("species", 0), "genus_level": ranks.get("genus", 0),
                           "unassigned": ranks.get("none", 0), "result": compare(truth, call)})
        stats = read_stats(Path(result_dir) / "stats" / f"{run}.tsv")
        qc.append({"run": run, "sample": runs[run]["sample_alias"]} |
                  {f"raw_{k}": v for k, v in stats.get("raw", {}).items()} |
                  {f"filtered_{k}": v for k, v in stats.get("filtered", {}).items()})

    sensitivity = []
    for identity in config["sensitivity"]["identity"]:
        for margin in config["sensitivity"]["margin"]:
            thresholds = base | {"min_identity": identity, "min_margin_to_second": margin}
            results = Counter()
            for run, hits in hits_by_run.items():
                truth = truth_species(runs[run]["sample_title"])
                call, support = sample_call([assign(rows, thresholds) for rows in hits.values()])
                results[compare(truth, call)] += 1
            sensitivity.append({"min_identity": identity, "min_margin": margin,
                                "correct_species": results["correct species"], "correct_genus": results["correct genus"],
                                "wrong": results["wrong"], "no_call": results["no call"],
                                "false_id_rate": round(results["wrong"] / max(1, len(hits_by_run)), 3)})

    for path, rows in [(out_validation, validation), (out_sensitivity, sensitivity), (out_qc, qc)]:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
