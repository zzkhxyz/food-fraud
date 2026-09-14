import argparse
import csv
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

API = "https://portal.boldsystems.org/api"
csv.field_size_limit(1 << 30)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "food-fraud-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read().decode()


def resolve(taxon):
    data = json.loads(get(f"{API}/query/preprocessor?query={urllib.parse.quote(taxon)}"))
    terms = data.get("successful_terms", [])
    for t in terms:
        if t["matched"].startswith("tax:"):
            return t["matched"]
    return None


def download_taxon(query):
    q = urllib.parse.quote(query)
    query_id = json.loads(get(f"{API}/query?query={q}&extent=full"))["query_id"]
    text = get(f"{API}/documents/{query_id}/download?format=tsv")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out", default="data/reference")
    args = parser.parse_args()

    config = yaml.safe_load(open(args.config))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    keep = ["processid", "sampleid", "insdc_acs", "marker_code", "identification", "identification_rank",
            "species", "genus", "family", "order", "class", "bin_uri", "inst", "country/ocean",
            "identification_method", "nuc_basecount", "nuc"]
    all_rows = []
    for taxon in config["reference"]["bold_taxa"]:
        query = resolve(taxon)
        if query is None:
            print(f"{taxon}: not found in BOLD")
            continue
        rows = download_taxon(query)
        print(f"{taxon}: {query} -> {len(rows)} records")
        for r in rows:
            all_rows.append({k: r.get(k, "") for k in keep} | {"query_taxon": taxon})
        time.sleep(1)

    with open(out / "bold_records.tsv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keep + ["query_taxon"], delimiter="\t")
        writer.writeheader()
        writer.writerows(all_rows)

    n = 0
    with open(out / "bold_coi.fasta", "w") as f:
        for r in all_rows:
            if r["marker_code"] != "COI-5P" or not r["nuc"]:
                continue
            if r["identification_rank"] not in ("species", "subspecies"):
                continue
            name = r["species"].replace(" ", "_")
            f.write(f">{r['processid']}|{name}|BOLD\n{r['nuc'].replace('-', '')}\n")
            n += 1
    print(f"saved {len(all_rows)} records, {n} COI-5P species-level sequences")


if __name__ == "__main__":
    main()
