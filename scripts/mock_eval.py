import csv
import sys
from collections import Counter
from pathlib import Path


def main():
    runs_tsv, truth_tsv, result_dir, out = sys.argv[1:5]
    runs = {r["run_accession"]: r for r in csv.DictReader(open(runs_tsv), delimiter="\t")}
    names = {r["common_name"]: r["species"] for r in csv.DictReader(open(truth_tsv), delimiter="\t")}

    rows = []
    for run in sorted(runs):
        path = Path(result_dir) / "assign" / f"{run}.tsv"
        if not path.exists():
            continue
        expected = {names[n.strip()] for n in runs[run]["sample_title"].split(",") if n.strip() in names}
        assignments = list(csv.DictReader(open(path), delimiter="\t"))
        species = Counter(a["assigned"] for a in assignments if a["rank"] == "species")
        total = len(assignments)
        detected = {s for s, n in species.items() if n / total >= 0.01}
        false_species = detected - expected
        missed = expected - detected
        false_reads = sum(n for s, n in species.items() if s not in expected)
        rows.append({"run": run, "sample": runs[run]["sample_alias"], "expected": "; ".join(sorted(expected)),
                     "detected": "; ".join(f"{s} ({n / total:.1%})" for s, n in species.most_common() if n / total >= 0.01),
                     "reads": total, "species_level_reads": sum(species.values()),
                     "missed": "; ".join(sorted(missed)), "false_species": "; ".join(sorted(false_species)),
                     "false_read_fraction": round(false_reads / total, 4) if total else 0})

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
