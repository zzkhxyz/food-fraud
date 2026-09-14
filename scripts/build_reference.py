import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from Bio import SeqIO

csv.field_size_limit(1 << 30)
MARKERS = ["COI", "16S", "12S", "CYTB"]


def clean_species(name):
    name = re.sub(r"\s+", " ", name.strip())
    if " x " in name or "hybrid" in name.lower():
        return None
    parts = name.split(" ")
    if len(parts) < 2:
        return None
    if not parts[1].isalpha() or not parts[1].islower() or parts[1] == "sp":
        return None
    return f"{parts[0]} {parts[1]}"


def read_bold(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))
    records = []
    bins = defaultdict(set)
    for r in rows:
        species = clean_species(r["species"])
        if r["marker_code"] != "COI-5P" or not r["nuc"] or species is None:
            continue
        seq = r["nuc"].replace("-", "").upper()
        if len(seq) < 400:
            continue
        records.append({"id": r["processid"], "species": species, "genus": r["genus"], "family": r["family"],
                        "bin": r["bin_uri"], "source": "BOLD", "marker": "COI", "seq": seq})
        if r["bin_uri"]:
            bins[r["bin_uri"]].add(species)
    return records, bins


def read_refseq(path, marker, taxonomy):
    records = []
    for rec in SeqIO.parse(path, "fasta"):
        acc, name, _ = rec.id.split("|")
        species = clean_species(name.replace("_", " "))
        if species is None:
            continue
        genus = species.split(" ")[0]
        records.append({"id": acc, "species": species, "genus": genus, "family": taxonomy.get(acc, ""),
                        "bin": "", "source": "RefSeq", "marker": marker, "seq": str(rec.seq).upper()})
    return records


def dedupe(records):
    seen = set()
    kept = []
    for r in records:
        key = (r["species"], r["seq"])
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)
    return kept


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="data/reference")
    args = parser.parse_args()
    ref = Path(args.ref)
    db = ref / "db"
    db.mkdir(exist_ok=True)

    bold, bins = read_bold(ref / "bold_records.tsv")
    shared_bins = {b: s for b, s in bins.items() if len(s) > 1}
    refseq_tax = {r["accession"]: r["query_taxon"] for r in csv.DictReader(open(ref / "refseq_records.tsv"), delimiter="\t")}

    all_records = {m: [] for m in MARKERS}
    all_records["COI"].extend(bold)
    for m in MARKERS:
        all_records[m].extend(read_refseq(ref / f"refseq_{m}.fasta", m, refseq_tax))

    with open(ref / "taxonomy.tsv", "w", newline="") as tax:
        writer = csv.writer(tax, delimiter="\t")
        writer.writerow(["seq_id", "marker", "species", "genus", "family", "source", "bin", "bin_shared"])
        for m in MARKERS:
            records = dedupe(all_records[m])
            with open(db / f"{m}.fasta", "w") as f:
                for r in records:
                    seq_id = f"{r['id']}|{r['species'].replace(' ', '_')}|{r['source']}"
                    f.write(f">{seq_id}\n{r['seq']}\n")
                    writer.writerow([seq_id, m, r["species"], r["genus"], r["family"], r["source"], r["bin"],
                                     r["bin"] in shared_bins])
            n_species = len({r["species"] for r in records})
            print(f"{m}: {len(records)} sequences, {n_species} species "
                  f"(BOLD {sum(r['source'] == 'BOLD' for r in records)}, RefSeq {sum(r['source'] == 'RefSeq' for r in records)})")

    with open(ref / "shared_bins.tsv", "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["bin", "n_species", "species"])
        for b, species in sorted(shared_bins.items(), key=lambda x: -len(x[1])):
            writer.writerow([b, len(species), "; ".join(sorted(species))])
    print(f"BOLD BINs: {len(bins)}, shared by more than one species: {len(shared_bins)}")

    bold_species = {r["species"] for r in bold}
    refseq_species = {r["species"] for r in all_records["COI"] if r["source"] == "RefSeq"}
    print(f"COI species only in BOLD: {len(bold_species - refseq_species)}, only in RefSeq: {len(refseq_species - bold_species)}, "
          f"in both: {len(bold_species & refseq_species)}")


if __name__ == "__main__":
    main()
