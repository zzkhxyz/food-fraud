import csv
import sys
from collections import Counter


def main():
    taxonomy, shared_bins, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = list(csv.DictReader(open(taxonomy), delimiter="\t"))
    bins = list(csv.DictReader(open(shared_bins), delimiter="\t"))

    lines = []
    for marker in sorted({r["marker"] for r in rows}):
        sub = [r for r in rows if r["marker"] == marker]
        by_source = Counter(r["source"] for r in sub)
        species = {r["species"] for r in sub}
        shared = sum(1 for r in sub if r["bin_shared"] == "True")
        lines.append({"marker": marker, "sequences": len(sub), "species": len(species),
                      "from_BOLD": by_source.get("BOLD", 0), "from_RefSeq": by_source.get("RefSeq", 0),
                      "sequences_in_shared_BIN": shared})

    coi = [r for r in rows if r["marker"] == "COI"]
    bold_species = {r["species"] for r in coi if r["source"] == "BOLD"}
    refseq_species = {r["species"] for r in coi if r["source"] == "RefSeq"}
    lines.append({"marker": "COI species overlap", "sequences": "", "species": len(bold_species & refseq_species),
                  "from_BOLD": len(bold_species - refseq_species), "from_RefSeq": len(refseq_species - bold_species),
                  "sequences_in_shared_BIN": ""})
    lines.append({"marker": "shared BINs", "sequences": len(bins), "species": sum(int(b["n_species"]) for b in bins),
                  "from_BOLD": "", "from_RefSeq": "", "sequences_in_shared_BIN": ""})

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=lines[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(lines)


if __name__ == "__main__":
    main()
