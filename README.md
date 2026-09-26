# Food Fraud: Is the Label Telling the Truth?

Course Project 04, Introduction to Bioinformatics, Astana IT University.
Author: Zhan Tabuldinov, BDA-2401.

Live results dashboard: https://food-fraud.vercel.app
Full report: [`report/Food_Fraud_Report.pdf`](report/Food_Fraud_Report.pdf)

This project checks whether the species written on a seafood label is really the species inside
the product. Seafood is one of the most mislabelled foods in the world. After a fish is filleted,
breaded, minced into surimi or cooked, a person cannot tell the species by eye any more. DNA stays
in the tissue, so I read the DNA and compare it with the label.

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

Identification works by similarity. I compare a read from the product against many reference
sequences of known species. If the best match is very close (high identity and good coverage) and
clearly better than the second-best species, the species call is trusted. If the match is weaker,
only the genus is trusted, or the read stays unassigned. This logic is controlled by the thresholds
in `config.yaml`, so a reader can see and change every number.

## Data

All data is public. The repository stores only a small test set; the real reads are downloaded by
the fetch scripts, which read the run list from the ENA portal API and check every file with its MD5
sum. Retrieval date for all sources: 2026-09-11.

| Dataset | Accession | Platform | What it is | Size |
|---|---|---|---|---|
| Market samples | PRJNA766222 | Illumina NextSeq 500, 2x125 bp | 20 processed seafood products from the Italian market, mitochondrial 16S amplicon | 318 MB |
| Single-source truth set | PRJNA1272083 | Oxford Nanopore MinION | animal samples of known species, four mitochondrial mini-barcodes; I use 17 fish and prawn samples | 199 MB |
| Mock mixtures | PRJEB39300 | Oxford Nanopore MinION | mixtures of cod, haddock, whiting and wolffish with known composition | 3.3 GB in total, 10 runs used (209 MB) |
| Reference, COI | BOLD Systems v5 API | - | COI barcodes for 19 commercial fish and prawn families | 54,112 records |
| Reference, mitogenomes | NCBI RefSeq | - | complete mitochondrial genomes of fish, sharks, lampreys, crustaceans and molluscs | about 5,100 records |

The **market samples** are the real question: 20 products bought in shops (burgers, fish sticks,
nuggets, surimi). The **single-source truth set** is a control: each sample is one known species, so
I can measure how often the method is right. The **mock mixtures** are a second control: they
contain several known species in known proportions, which tests whether the method can detect more
than one species in one product.

## Reference database

The reference is built by `scripts/build_reference.py` from two sources:

- **BOLD Systems v5** gives COI barcodes at family level for 19 target families (cod, hake,
  mackerel, swordfish, salmon, herring, anchovy, sea bass, sea bream, mullet, wolffish, flatfish,
  sole, sharks, rays, lamprey, prawn and others). Records without a proper species name, hybrids and
  sequences shorter than 400 bp are removed.
- **NCBI RefSeq** gives complete mitochondrial genomes; the four markers (COI, 16S, 12S, CYTB) are
  cut out of the genome annotation.

Sizes produced on the retrieval date:

| Marker | Sequences | Species | From BOLD | From RefSeq |
|---|---|---|---|---|
| COI | 29,200 | 5,813 | 24,282 | 4,918 |
| 16S | 4,939 | 4,885 | 0 | 4,939 |
| 12S | 4,922 | 4,885 | 0 | 4,922 |
| CYTB | 4,922 | 4,891 | 0 | 4,922 |

The two sources are compared against each other (`results/reference/cross_check.tsv`): every RefSeq
COI sequence is searched against the whole COI reference with BLAST. Of 508 comparisons, 287 name the
same species in both databases, 64 name another species of the same genus, and 157 name a different
genus. My rule for these conflicts: both sources stay in the reference, but a read is called to
species only when its best species beats the second species by at least 2 identity points. When two
names tie, the call drops to genus level, so a naming conflict between the databases cannot turn into
a confident wrong species.

## Method

### Illumina short reads (market samples)

1. **Quality control** with `fastp`: trim low-quality tails (Q20) and drop reads shorter than 100 bp.
2. **Merge pairs** with `vsearch`: the forward and reverse read of one 16S amplicon overlap, so they
   are merged into one longer sequence (19 of 20 runs merge 84-99% of pairs, mean fragment about
   207 bp; one surimi run, SRR16088625, merges only 26%, so its composition rests on fewer reads).
3. **Denoise** with `vsearch` (UNOISE): group nearly identical sequences into ASVs
   (amplicon sequence variants) and remove errors and chimeras. An ASV is a clean, representative
   sequence with a read count.
4. **Identify** each ASV with `blastn` against the 16S reference, then apply the thresholds.
5. **Summarise**: turn ASV counts into a species composition per product and compare it with the
   label.

### Nanopore long reads (truth set and mock mixtures)

1. **Filter** with `chopper`: keep reads between 80 and 2,000 bp with mean quality Q10 or higher;
   subsample very large runs to 20,000 reads for speed.
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

### Runtime

The full run is 204 Snakemake jobs. Measured with Snakemake benchmarks on a laptop with 8 CPU cores
and Docker limited to 4 GB of memory:

| Step | Jobs | Total time | Peak memory |
|---|---|---|---|
| fastp | 20 | 170 s | 1.2 GB |
| vsearch denoise | 20 | 486 s | 23 MB |
| blastn (ASVs) | 20 | 37 s | 98 MB |
| minimap2 (Nanopore) | 27 | 617 s | 451 MB |
| BOLD vs RefSeq cross-check | 1 | 177 s | 164 MB |

## Outputs

- `results/illumina/label_vs_content.tsv` - the main table: label vs DNA for every product, with a
  verdict.
- `results/illumina/composition.tsv` - full species composition of every product.
- `results/illumina/qc_summary.tsv` - read counts, quality and merge rate per run.
- `results/nanopore/validation.tsv` - species call for each single-source sample against the truth.
- `results/nanopore/sensitivity.tsv` - false identification rate for every threshold combination.
- `results/nanopore/qc_summary.tsv` - read length and quality before and after filtering.
- `results/mock/mock_eval.tsv` - detected vs expected genera in the mock mixtures.
- `results/reference/reference_stats.tsv`, `results/reference/cross_check.tsv` - reference size and
  BOLD vs RefSeq agreement.
- `results/benchmarks/` - run time and memory of every step.

## Results summary

Full run on all 20 market products, 17 single-source Nanopore samples and 10 mock mixtures.

**Market products (Illumina).** Of the 20 products, 4 confirm the label, 1 does not, and 15 carry
only a generic "fish" label, so they cannot be confirmed or denied by name; for these I still
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
at genus level, and 5 are wrong. The Nanopore reads have a mean quality of about Q13, which means
about 5% errors per read, so a single read rarely reaches the 97% identity needed for a species
call. The genus is found reliably; close species are not separated. In all five wrong calls the called
taxon is supported by less than 5% of the reads, so these are weak calls, not confident errors.

**Mock mixtures (Nanopore).** The mixtures are evaluated at genus level, because single mini-barcodes
rarely separate close species (a genus counts as detected at 1% of reads or more). Five of the ten runs
have thousands of assigned reads. In these five runs 11 of the 13 expected genera are found: the
cod-haddock-whiting mix `CHW1a_1` and the cod-wolffish mix `SWp` are fully recovered, and the
four-species `Silage_day_21` shows cod and wolffish but misses the minor haddock and whiting. The
single-species haddock and whiting runs leak 27% and 13% of assigned reads to the other two cod-family
genera, which are very close relatives. The other five runs have only 2 to 12 assigned reads, too few to
judge. So the pipeline can report more than one fish in a product, but a small component of a close
relative can be missed or confused.

## Limitations

- The reference is not complete for every species. The salmon result shows that a missing reference
  can turn into "unassigned" reads instead of a wrong call, which is the safer failure but still a
  gap.
- Short 16S amplicons and single Nanopore barcodes often resolve the genus but not the exact species
  inside a genus.
- Nanopore reads are identified one by one. With about 5% error per read, species-level calls need a
  consensus of many reads, which this pipeline does not build.
- There is no rule for a minimum share of supporting reads, so a sample where the top taxon has only
  1-4% of the reads still gets a (weak) call.
- Subsampling large Nanopore runs speeds up the run but lowers sensitivity for rare components in a
  mixture.
- Inside the cod family (Gadus, Melanogrammus, Merlangius) Nanopore reads partly cross-assign between
  genera, so a minor cod-family component in a mixture cannot be confirmed from these reads alone.

## Conclusions

Seafood is easy to mislabel because a processed product no longer looks like a fish. This project
shows that reading the DNA from the product and comparing it with a reference of known species is a
practical way to check the label, even for burgers, fish sticks and surimi.

My main conclusions are:

1. **The method works, and I measured how well.** On the single-source control samples the pipeline
   finds the correct genus in 12 of 17 cases, but it rarely separates very close species inside the
   same genus. So a result like "this is cod or a close relative of cod" is reliable, while the exact
   species is not always certain. This is a measured limit of a short single marker, not a guess.

2. **The named products match their label.** Where the label states a species (tuna, swordfish, sea
   bass), the DNA agrees. I found no clear species swap in these branded products.

3. **The surimi products are the interesting case.** These carry only a generic "fish" label. The
   DNA often shows cheap small pelagic fish such as sardine, mackerel and anchovy instead of the
   Alaska pollock usually expected in surimi. This is not illegal, because no species was promised,
   but the buyer cannot know what fish they eat. As expected, the "crab flavour" surimi contains no
   crab DNA, because the taste comes from an additive.

4. **One product could not be identified, and that is safe behaviour.** Almost all reads of the
   salmon burger stayed unassigned, most likely because the reference lacks enough salmon sequences.
   The method answered "unknown" instead of giving a wrong species, which is the safer type of
   error.

Overall, DNA barcoding can verify seafood labels even after heavy processing. In this sample the main
signal is not a hidden swap of an expensive species for a cheap one under a false name, but a lack of
detail: products without a species name that in fact use cheaper fish. The confidence of every call
depends on how complete the reference database is; where a reference is missing, the method returns
"unassigned" rather than a false result.

## Web dashboard

An interactive summary of the results lives in `web/` and is published at
https://food-fraud.vercel.app. It is a single static page that reads a small `web/data.json` file, so
it needs no server code and can be hosted anywhere.

Rebuild the data file from the results after a run:

```
python scripts/build_web_data.py results web/data.json
```

Preview it locally:

```
python -m http.server -d web 8000
```

Then open `http://localhost:8000`. To publish it, run `vercel deploy --prod` inside `web/`.

## Layout

- `config.yaml` - accessions, reference taxa, QC parameters and identification thresholds.
- `labels.tsv` - product labels and the species each label implies.
- `mock_truth.tsv` - species in the mock mixtures.
- `scripts/` - fetch, reference building, identification and summary scripts.
- `Snakefile` - the workflow that connects every step.
- `environment.yml`, `Dockerfile`, `docker-compose.yml` - the locked, reproducible environment.
- `test_data/` - one small run per dataset for the quick test.
- `report/` - the written report, its figures and the scripts that build them.
- `web/` - a static dashboard of the results.

## Contribution statement

This is an individual project. Zhan Tabuldinov designed and carried out all parts of the work: choice
of datasets, data retrieval and the reference database, the Illumina and Nanopore processing, the
identification rules and sensitivity analysis, the Snakemake workflow and Docker environment, the
dashboard and the report.

## Use of AI assistants

I used Claude (Anthropic) through Claude Code as a coding and writing assistant: to help write and
debug the Python scripts and the Snakemake rules, to find and fix parsing bugs in the summary
scripts, to build the web dashboard and to edit the English text of this README and the report. All
datasets, thresholds and conclusions were chosen and checked by me, and I can explain every part of
the code.
