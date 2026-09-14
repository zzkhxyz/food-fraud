import argparse
import csv
import hashlib
import io
import urllib.request
from pathlib import Path

import yaml

ENA_URL = ("https://www.ebi.ac.uk/ena/portal/api/filereport?accession={acc}&result=read_run"
           "&fields=run_accession,sample_accession,sample_title,sample_alias,library_name,"
           "instrument_model,read_count,base_count,fastq_bytes,fastq_md5,fastq_ftp&format=tsv")


def fetch_run_table(bioproject):
    with urllib.request.urlopen(ENA_URL.format(acc=bioproject), timeout=120) as r:
        text = r.read().decode()
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, md5):
    if dest.exists() and md5_of(dest) == md5:
        print(f"  skip {dest.name} (already ok)")
        return
    print(f"  get  {dest.name}")
    urllib.request.urlretrieve("https://" + url, dest)
    if md5_of(dest) != md5:
        dest.unlink()
        raise RuntimeError(f"md5 mismatch for {dest}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=["illumina", "nanopore_single_source", "nanopore_mock"])
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--max-runs", type=int, default=0)
    parser.add_argument("--match", default="")
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load(open(args.config))
    bioproject = config[args.dataset]["bioproject"]
    out_dir = Path("data/raw") / args.dataset
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = fetch_run_table(bioproject)
    with open(out_dir / "runs.tsv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=runs[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(runs)
    print(f"{bioproject}: {len(runs)} runs listed in {out_dir / 'runs.tsv'}")

    if args.match:
        terms = [t.strip().lower() for t in args.match.split(",")]
        runs = [r for r in runs if any(t in (r["library_name"] + " " + r["sample_title"] + " " + r["sample_alias"]).lower() for t in terms)]
    if args.max_runs:
        runs = runs[: args.max_runs]
    total_mb = sum(int(b) for r in runs for b in r["fastq_bytes"].split(";")) / 1e6
    print(f"selected {len(runs)} runs, {total_mb:.0f} MB")
    if args.no_download:
        return

    for r in runs:
        urls = r["fastq_ftp"].split(";")
        md5s = r["fastq_md5"].split(";")
        for url, md5 in zip(urls, md5s):
            download(url, out_dir / url.split("/")[-1], md5)


if __name__ == "__main__":
    main()
