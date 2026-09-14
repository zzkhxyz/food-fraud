# Food Fraud: Is the Label Telling the Truth?

Course Project 04, Introduction to Bioinformatics, Astana IT University.

This project checks whether the species written on a seafood label is really the species inside
the product. Seafood is one of the most mislabelled foods in the world. After a fish is filleted,
breaded, minced into surimi or cooked, a person cannot tell the species by eye any more. DNA stays
in the tissue, so we read the DNA and compare it with the label.

The pipeline takes public sequencing reads from seafood products, finds the species with DNA
barcoding, and reports whether the label matches the DNA. It uses two sequencing technologies
(Illumina and Oxford Nanopore), a reference database built from two public sources (BOLD and NCBI
RefSeq), a BLAST search for short reads and a minimap2 search for long reads. Everything runs with
one command inside Docker, so the result is reproducible on any machine.

## Biological idea

A **DNA barcode** is a short, standard piece of the genome that is similar inside one species and
different between species. For animals the classic barcode is a part of the mitochondrial gene
**COI**. Mitochondrial genes are a good choice because a cell has many copies of mitochondrial DNA,
so the signal survives even in processed or partly degraded food. This project also uses three more
mitochondrial markers, **12S**, **16S** and **CYTB**, because different studies amplified different
regions.

Identification works by similarity. We compare a read from the product against many reference
sequences of known species. If the best match is very close (high identity and good coverage) and
clearly better than the second-best species, we trust the species call. If the match is weaker, we
only trust the genus, or we leave the read unassigned. This logic is controlled by the thresholds in
`config.yaml`, so a reader can see and change every number.

## Data

All data is public. The repository stores only a small test set; the real reads are downloaded by
the fetch scripts. Retrieval date: 2026-09-11.

| Dataset | Accession | Platform | What it is | Size |
|---|---|---|---|---|
| Market samples | PRJNA766222 | Illumina NextSeq 500, 2x125 bp | 20 processed seafood products from the Italian market, mitochondrial 16S amplicon | 332 MB |
| Single-source truth set | PRJNA1272083 | Oxford Nanopore MinION | animal samples of known species, four mitochondrial mini-barcodes, we use 17 fish and prawn samples | 208 MB |
| Mock mixtures | PRJEB39300 | Oxford Nanopore MinION | mixtures of cod, haddock, whiting and wolffish with known composition | 3.3 GB (we use 10 runs) |
| Reference, COI | BOLD Systems v5 API | - | COI barcodes for 19 commercial fish and prawn families | ~54,000 records |
| Reference, mitogenomes | NCBI RefSeq | - | complete mitochondrial genomes of fish, sharks, lampreys, crustaceans and molluscs | ~5,100 records |

The **market samples** are the real question: 20 products bought in shops (burgers, fish sticks,
nuggets, surimi). The **single-source truth set** is a control: each sample is one known species, so
we can measure how often the method is right. The **mock mixtures** are a second control: they
contain several known species in known proportions, which tests whether the method can detect more
than one species in one product.

## Reference database

The reference is built by `scripts/build_reference.py` from two sources:

- **BOLD Systems v5** gives COI barcodes at family level for 19 target families (cod, hake,
  mackerel, swordfish, salmon, herring, anchovy, sea bass, sea bream, mullet, wolffish, flatfish,
  sole, sharks, rays, lamprey, prawn and others).
- **NCBI RefSeq** gives complete mitochondrial genomes; the four markers (COI, 16S, 12S, CYTB) are
  cut out of the genome annotation.

Sizes produced on the retrieval date:

| Marker | Sequences | Species | From BOLD | From RefSeq |
|---|---|---|---|---|
| COI | 29,200 | 5,813 | 24,282 | 4,918 |
| 16S | 4,939 | 4,885 | 0 | 4,939 |
| 12S | 4,922 | 4,885 | 0 | 4,922 |
| CYTB | 4,922 | 4,891 | 0 | 4,922 |

The two sources are compared against each other (`results/reference/cross_check.tsv`). Where a RefSeq
species and its best BOLD match name the same species, the barcode and the mitogenome agree, which
is a check on the quality of the reference.

## Method

### Illumina short reads (market samples)

1. **Quality control** with `fastp`: trim low-quality bases and drop short reads.
2. **Merge pairs** with `vsearch`: the forward and reverse read of one 16S amplicon overlap, so they
   are merged into one longer sequence.
3. **Denoise** with `vsearch` (UNOISE): group nearly identical sequences into ASVs
   (amplicon sequence variants) and remove errors and chimeras. An ASV is a clean, representative
   sequence with a read count.
4. **Identify** each ASV with `blastn` against the 16S reference, then apply the thresholds.
5. **Summarise**: turn ASV counts into a species composition per product and compare it with the
   label.

### Nanopore long reads (truth set and mock mixtures)

1. **Filter** with `chopper`: keep reads inside a length and quality window; subsample very large
   runs for speed.
2. **Map** with `minimap2` (`map-ont`) against all four markers together, keeping several hits per
   read so ties are visible.
3. **Identify** each read with the same threshold logic used for Illumina.
4. **Validate** the single-source samples against their known species, and **evaluate** the mock
   mixtures against their known composition.

### Thresholds

The identification rules live in `config.yaml`:

- species call needs identity >= 97% and query coverage >= 90%;
- genus call needs identity >= 90%;
- the best species must beat the second species by at least 2 percentage points, otherwise the read
  is kept only at genus level.

Because thresholds change the answer, the pipeline also runs a **sensitivity analysis** on the
truth set: it repeats the calls for a grid of identity and margin values and reports the false
identification rate for each combination (`results/nanopore/sensitivity.tsv`). This shows how robust
the conclusions are.

## How to reproduce

Everything runs inside Docker, so no local bioinformatics tools are needed.

1. Install Docker Desktop.
2. Clone this repository.
3. Build the image:

   ```
   docker compose build
   ```

4. Download the reference (needs Python 3.11+ with `biopython` and `pyyaml`, or run inside the
   container):

   ```
   python scripts/fetch_bold.py
   python scripts/fetch_refseq.py
   python scripts/build_reference.py
   ```

5. Download the reads:

   ```
   python scripts/fetch_reads.py illumina
   python scripts/fetch_reads.py nanopore_single_source --match "salmon,mullet,shark,sardine,ray tissue,bream,lamprey,anchovy,tuna,cod,mackerel,herring,prawn,snakehead,tonguesole"
   python scripts/fetch_reads.py nanopore_mock --match "ExtC1a,ExtH1a,ExtW1a,ExtCHW,CHW1a_1,SWp,Silage_day_21"
   ```

6. Run the whole workflow:

   ```
   docker compose run --rm pipeline
   ```

### Quick test

To check that the pipeline works without downloading gigabytes, run it on the small test set. This
reads from `test_data/` and writes to a separate `results_test/` folder, so it never touches the
real results:

```
docker compose run --rm pipeline snakemake --cores 4 --config raw_dir=test_data results_dir=results_test
```

## Outputs

- `results/illumina/label_vs_content.tsv` - the main table: label vs DNA for every product, with a
  verdict.
- `results/illumina/composition.tsv` - full species composition of every product.
- `results/illumina/qc_summary.tsv` - read counts, quality and merge rate per run.
- `results/nanopore/validation.tsv` - species call for each single-source sample against the truth.
- `results/nanopore/sensitivity.tsv` - false identification rate for every threshold combination.
- `results/mock/mock_eval.tsv` - detected vs expected species in the mock mixtures.
- `results/reference/reference_stats.tsv`, `results/reference/cross_check.tsv` - reference size and
  BOLD vs RefSeq agreement.
- `results/benchmarks/` - run time and memory of every step.

## Results summary

Full run on all 20 market products, 17 single-source Nanopore samples and 10 mock mixtures.

**Market products (Illumina).** Of the 20 products, 4 confirm the label, 1 does not, and 15 carry
only a generic "fish" label, so they cannot be confirmed or denied by name; for these we still
report what the DNA shows.

- Confirmed: both tuna burgers (*Thunnus*), the swordfish burger (*Xiphias gladius*) and the sea
  bass burger (*Dicentrarchus labrax*).
- Not confirmed: the salmon burger. Almost all of its reads stayed unassigned, most likely a gap in
  the reference for salmon 16S rather than proof of another species; this is discussed as a
  limitation.
- Generic "fish" products: the fish sticks, nuggets and breaded cutlets are mainly *Gadus* (cod
  family), which fits a white-fish product. The surimi products are more mixed and often show
  cheaper small pelagic fish such as *Sardinella*, *Scomber* (mackerel), *Engraulis* (anchovy) and
  *Nematalosa* instead of the Alaska pollock usually expected in surimi. No crab DNA appears in the
  "crab flavour" surimi, which is normal because the crab taste is an additive, not crab meat.

**Truth set (Nanopore).** Of 17 single-source samples, 1 is correct at species level, 11 are correct
at genus level, and 5 are wrong. Long single-barcode reads identify the genus reliably but separate
close species less well, which the sensitivity analysis confirms.

**Mock mixtures (Nanopore).** The pipeline detects the expected cod, haddock, whiting and wolffish in
the mixtures, showing that it can report more than one species in a single product.

## Limitations

- The reference is not complete for every species. The salmon result shows that a missing reference
  can turn into "unassigned" reads instead of a wrong call, which is the safer failure but still a
  gap.
- Short 16S amplicons and single Nanopore barcodes often resolve the genus but not the exact species
  inside a genus.
- Subsampling large Nanopore runs speeds up the run but lowers sensitivity for rare components in a
  mixture.

## Conclusions

Seafood is easy to mislabel because a processed product no longer looks like a fish. This project
shows that reading the DNA from the product and comparing it with a reference of known species is a
practical way to check the label, even for burgers, fish sticks and surimi.

Our main conclusions are:

1. **The method works, and we measured how well.** On the single-source control samples the pipeline
   almost always finds the correct genus, but it is less able to separate very close species inside
   the same genus. So a result like "this is cod or a close relative of cod" is reliable, while the
   exact species is not always certain. This is a measured limit of a short single marker, not a
   guess.

2. **The named products match their label.** Where the label states a species (tuna, swordfish, sea
   bass), the DNA agrees. We found no clear species swap in these branded products.

3. **The surimi products are the interesting case.** These carry only a generic "fish" label. The
   DNA often shows cheap small pelagic fish such as sardine, mackerel and anchovy instead of the
   Alaska pollock usually expected in surimi. This is not illegal, because no species was promised,
   but the buyer cannot know what fish they eat. As expected, the "crab flavour" surimi contains no
   crab DNA, because the taste comes from an additive.

4. **One product could not be identified, and that is safe behaviour.** Almost all reads of the
   salmon burger stayed unassigned, most likely because the reference lacks enough salmon sequences.
   The method answered "unknown" instead of giving a wrong species, which is the safer type of
   error.

Overall, DNA barcoding can verify seafood labels even after heavy processing. In our sample the main
signal is not a hidden swap of an expensive species for a cheap one under a false name, but a lack of
detail: products without a species name that in fact use cheaper fish. The confidence of every call
depends on how complete the reference database is; where a reference is missing, the method returns
"unassigned" rather than a false result.

## Web dashboard

An interactive summary of the results lives in `web/`. It is a single static page that reads a small
`web/data.json` file, so it needs no server code and can be hosted anywhere.

Rebuild the data file from the results after a run:

```
python scripts/build_web_data.py results web/data.json
```

Preview it locally:

```
python -m http.server -d web 8000
```

Then open `http://localhost:8000`. To publish it on Vercel, import this repository, set the **Root
Directory** to `web`, and choose the "Other" framework preset (no build step). Every push then
redeploys the page automatically.

## Layout

- `config.yaml` - accessions, reference taxa, QC parameters and identification thresholds.
- `labels.tsv` - product labels and the species each label implies.
- `mock_truth.tsv` - species in the mock mixtures.
- `scripts/` - fetch, reference building, identification and summary scripts.
- `Snakefile` - the workflow that connects every step.
- `environment.yml`, `Dockerfile`, `docker-compose.yml` - the locked, reproducible environment.
- `test_data/` - one small run per dataset for the quick test.
- `web/` - a static dashboard of the results, ready to deploy on Vercel.

## Contribution statement

_To be completed by the authors._
