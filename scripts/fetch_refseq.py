import argparse
import csv
from pathlib import Path

import yaml
from Bio import Entrez, SeqIO

MARKERS = {
    "COI": {"type": "CDS", "genes": {"COX1", "CO1", "COI", "COXI"}},
    "CYTB": {"type": "CDS", "genes": {"CYTB", "COB", "CYB"}},
    "16S": {"type": "rRNA", "products": {"16S ribosomal RNA", "l-rRNA", "16S rRNA"}},
    "12S": {"type": "rRNA", "products": {"12S ribosomal RNA", "s-rRNA", "12S rRNA"}},
}


def feature_marker(feature):
    gene = {g.upper() for g in feature.qualifiers.get("gene", [])}
    product = set(feature.qualifiers.get("product", []))
    for marker, rule in MARKERS.items():
        if feature.type != rule["type"]:
            continue
        if rule["type"] == "CDS" and gene & rule["genes"]:
            return marker
        if rule["type"] == "rRNA" and product & rule["products"]:
            return marker
    return None


def search_ids(taxon, query, email):
    Entrez.email = email
    term = f"{taxon}[Organism] AND {query}"
    handle = Entrez.esearch(db="nucleotide", term=term, retmax=100000)
    ids = Entrez.read(handle)["IdList"]
    handle.close()
    return ids


def fetch_records(ids, batch=200):
    for i in range(0, len(ids), batch):
        handle = Entrez.efetch(db="nucleotide", id=",".join(ids[i:i + batch]), rettype="gb", retmode="text")
        yield from SeqIO.parse(handle, "genbank")
        handle.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out", default="data/reference")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    config = yaml.safe_load(open(args.config))
    ref = config["reference"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    fasta = {m: open(out / f"refseq_{m}.fasta", "w") for m in MARKERS}
    table = open(out / "refseq_records.tsv", "w", newline="")
    writer = csv.writer(table, delimiter="\t")
    writer.writerow(["accession", "organism", "taxid", "query_taxon", "length", "markers"])

    counts = {m: 0 for m in MARKERS}
    for taxon in ref["refseq_taxa"]:
        ids = search_ids(taxon, ref["refseq_query"], config["email"])
        if args.limit:
            ids = ids[: args.limit]
        print(f"{taxon}: {len(ids)} RefSeq mitogenomes")
        for record in fetch_records(ids):
            if not record.seq.defined:
                continue
            organism = record.annotations.get("organism", "unknown")
            taxid = next((x.split(":")[1] for f in record.features if f.type == "source"
                          for x in f.qualifiers.get("db_xref", []) if x.startswith("taxon:")), "")
            found = []
            for feature in record.features:
                marker = feature_marker(feature)
                if marker is None:
                    continue
                seq = feature.location.extract(record).seq
                name = organism.replace(" ", "_")
                fasta[marker].write(f">{record.id}|{name}|RefSeq\n{seq}\n")
                counts[marker] += 1
                found.append(marker)
            writer.writerow([record.id, organism, taxid, taxon, len(record), ",".join(found)])

    for f in fasta.values():
        f.close()
    table.close()
    print("sequences per marker:", counts)


if __name__ == "__main__":
    main()
