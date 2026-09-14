import csv
import sys
from collections import defaultdict


def main():
    hits, out = sys.argv[1], sys.argv[2]
    best = defaultdict(list)
    for line in open(hits):
        q, s, pident, length, qcovs, evalue, bitscore = line.rstrip("\n").split("\t")
        if s.endswith("|BOLD"):
            best[q].append((float(bitscore), float(pident), s))

    rows = []
    for q, lst in best.items():
        lst.sort(reverse=True)
        score, pident, s = lst[0]
        refseq_species = q.split("|")[1].replace("_", " ")
        bold_species = s.split("|")[1].replace("_", " ")
        same_genus = refseq_species.split(" ")[0] == bold_species.split(" ")[0]
        if refseq_species == bold_species:
            status = "agree"
        elif same_genus:
            status = "different species, same genus"
        else:
            status = "different genus"
        rows.append({"refseq_id": q.split("|")[0], "refseq_species": refseq_species, "best_bold_hit": s.split("|")[0],
                     "bold_species": bold_species, "identity": pident, "status": status})

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["status"], -float(r["identity"]))))


if __name__ == "__main__":
    main()
