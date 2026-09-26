import csv
import sys
from collections import Counter
from pathlib import Path

import yaml


def genus(name):
    return name.split(" ")[0]


def detected_taxa(counter, total, min_fraction):
    return {t for t, n in counter.items() if total and n / total >= min_fraction}


def main():
    runs_tsv, truth_tsv, result_dir, out = sys.argv[1:5]
    min_fraction = yaml.safe_load(open("config.yaml"))["mock"]["min_fraction"]
    runs = {r["run_accession"]: r for r in csv.DictReader(open(runs_tsv), delimiter="\t")}
    names = {r["common_name"]: r["species"] for r in csv.DictReader(open(truth_tsv), delimiter="\t")}

    rows = []
    for run in sorted(runs):
        path = Path(result_dir) / "assign" / f"{run}.tsv"
        if not path.exists():
            continue
        expected = {names[n.strip()] for n in runs[run]["sample_title"].split(",") if n.strip() in names}
        expected_genera = {genus(s) for s in expected}
        assignments = list(csv.DictReader(open(path), delimiter="\t"))
        total = len(assignments)
        species = Counter(a["assigned"] for a in assignments if a["rank"] == "species")
        genera = Counter(genus(a["assigned"]) for a in assignments if a["rank"] in ("species", "genus"))

        found_species = detected_taxa(species, total, min_fraction)
        found_genera = detected_taxa(genera, total, min_fraction)
        false_reads = sum(n for g, n in genera.items() if g not in expected_genera)
        assigned = sum(genera.values())

        rows.append({"run": run, "sample": runs[run]["sample_alias"],
                     "expected": "; ".join(sorted(expected)),
                     "detected_genus": "; ".join(f"{g} ({genera[g] / total:.1%})" for g in sorted(found_genera, key=lambda g: -genera[g])),
                     "detected_species": "; ".join(sorted(found_species)),
                     "missed_genus": "; ".join(sorted(expected_genera - found_genera)),
                     "false_genus": "; ".join(sorted(found_genera - expected_genera)),
                     "reads": total, "assigned_reads": assigned,
                     "species_level_reads": sum(species.values()),
                     "false_read_fraction": round(false_reads / assigned, 4) if assigned else 0})

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
