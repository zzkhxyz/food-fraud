import csv
from pathlib import Path

configfile: "config.yaml"

MARKERS = ["COI", "16S", "12S", "CYTB"]
RAW = config.get("raw_dir", "data/raw")
RES = config.get("results_dir", "results")
REF = "data/reference"


def runs_with_files(dataset):
    table = Path(RAW) / dataset / "runs.tsv"
    if not table.exists():
        return []
    found = []
    for row in csv.DictReader(open(table), delimiter="\t"):
        run = row["run_accession"]
        if (Path(RAW) / dataset / f"{run}_1.fastq.gz").exists():
            found.append(run)
    return found


ILLUMINA = runs_with_files("illumina")
NANO = runs_with_files("nanopore_single_source")
MOCK = runs_with_files("nanopore_mock")
THREADS = config["threads"]

wildcard_constraints:
    dataset="nanopore_single_source|nanopore_mock",
    run="[A-Z]+[0-9]+",


rule all:
    input:
        RES + "/reference/reference_stats.tsv",
        RES + "/reference/cross_check.tsv",
        RES + "/illumina/label_vs_content.tsv",
        RES + "/illumina/qc_summary.tsv",
        RES + "/nanopore/validation.tsv",
        RES + "/nanopore/sensitivity.tsv",
        RES + "/nanopore/qc_summary.tsv",
        RES + "/mock/mock_eval.tsv",


rule blast_db:
    input: REF + "/db/{marker}.fasta"
    output: REF + "/db/{marker}.nsq"
    shell: "makeblastdb -in {input} -dbtype nucl -out " + REF + "/db/{wildcards.marker} > /dev/null"


rule reference_stats:
    input: REF + "/taxonomy.tsv", REF + "/shared_bins.tsv"
    output: RES + "/reference/reference_stats.tsv"
    shell: "python scripts/reference_stats.py {input} {output}"


rule reference_cross_check:
    input: fasta=REF + "/db/COI.fasta", db=REF + "/db/COI.nsq"
    output: table=RES + "/reference/cross_check.tsv", hits=RES + "/reference/refseq_vs_bold.hits"
    params: query=RES + "/reference/refseq_coi.fasta", db=REF + "/db/COI"
    threads: THREADS
    benchmark: RES + "/benchmarks/cross_check.txt"
    shell:
        "seqkit grep -n -r -p 'RefSeq$' {input.fasta} > {params.query} && "
        "blastn -query {params.query} -db {params.db} "
        "-outfmt '6 qseqid sseqid pident length qcovs evalue bitscore' -max_target_seqs 5 -num_threads {threads} "
        "> {output.hits} && python scripts/cross_check.py {output.hits} {output.table}"


rule fastp:
    input:
        r1=RAW + "/illumina/{run}_1.fastq.gz",
        r2=RAW + "/illumina/{run}_2.fastq.gz",
    output:
        r1=RES + "/illumina/qc/{run}_1.fastq.gz",
        r2=RES + "/illumina/qc/{run}_2.fastq.gz",
        json=RES + "/illumina/qc/{run}.fastp.json",
        html=RES + "/illumina/qc/{run}.fastp.html",
    threads: 4
    benchmark: RES + "/benchmarks/fastp_{run}.txt"
    shell:
        "fastp -i {input.r1} -I {input.r2} -o {output.r1} -O {output.r2} "
        "--qualified_quality_phred {config[illumina_qc][min_quality]} "
        "--length_required {config[illumina_qc][min_length]} "
        "--cut_tail --cut_tail_mean_quality {config[illumina_qc][min_quality]} "
        "--json {output.json} --html {output.html} --thread {threads} 2> /dev/null"


rule merge_pairs:
    input:
        r1=RES + "/illumina/qc/{run}_1.fastq.gz",
        r2=RES + "/illumina/qc/{run}_2.fastq.gz",
    output:
        merged=RES + "/illumina/merged/{run}.merged.fastq",
        log=RES + "/illumina/merged/{run}.merge.log",
    threads: 2
    shell:
        "vsearch --fastq_mergepairs {input.r1} --reverse {input.r2} --fastqout {output.merged} "
        "--fastq_minovlen {config[illumina_qc][min_overlap]} --fastq_maxdiffs {config[illumina_qc][max_diffs]} "
        "--fastq_allowmergestagger --threads {threads} 2> {output.log}"


rule denoise:
    input: RES + "/illumina/merged/{run}.merged.fastq"
    output:
        asv=RES + "/illumina/asv/{run}.asv.fasta",
        log=RES + "/illumina/asv/{run}.denoise.log",
    params: prefix=RES + "/illumina/asv/{run}"
    threads: 2
    benchmark: RES + "/benchmarks/denoise_{run}.txt"
    shell:
        "vsearch --fastq_filter {input} --fastq_maxee {config[illumina_qc][max_expected_errors]} "
        "--fastaout {params.prefix}.filtered.fasta 2> {output.log} && "
        "vsearch --derep_fulllength {params.prefix}.filtered.fasta --sizeout "
        "--minuniquesize 2 --output {params.prefix}.derep.fasta 2>> {output.log} && "
        "vsearch --cluster_unoise {params.prefix}.derep.fasta --minsize {config[illumina_qc][min_asv_size]} "
        "--sizein --sizeout --centroids {params.prefix}.unoise.fasta --threads {threads} 2>> {output.log} && "
        "vsearch --uchime3_denovo {params.prefix}.unoise.fasta --sizein --sizeout "
        "--nonchimeras {output.asv} 2>> {output.log}"


rule blast_asv:
    input: asv=RES + "/illumina/asv/{run}.asv.fasta", db=REF + "/db/16S.nsq"
    output: RES + "/illumina/blast/{run}.hits"
    params: db=REF + "/db/16S"
    threads: 4
    benchmark: RES + "/benchmarks/blast_{run}.txt"
    shell:
        "blastn -query {input.asv} -db {params.db} "
        "-outfmt '6 qseqid sseqid pident length qcovs evalue bitscore' -max_target_seqs 50 "
        "-num_threads {threads} > {output}"


rule identify_asv:
    input: RES + "/illumina/blast/{run}.hits"
    output: RES + "/illumina/assign/{run}.tsv"
    shell: "python scripts/identify.py {input} {output}"


rule summarize_illumina:
    input:
        assign=expand(RES + "/illumina/assign/{run}.tsv", run=ILLUMINA),
        asv=expand(RES + "/illumina/asv/{run}.asv.fasta", run=ILLUMINA),
        fastp=expand(RES + "/illumina/qc/{run}.fastp.json", run=ILLUMINA),
        merge=expand(RES + "/illumina/merged/{run}.merge.log", run=ILLUMINA),
    output:
        composition=RES + "/illumina/composition.tsv",
        label=RES + "/illumina/label_vs_content.tsv",
        qc=RES + "/illumina/qc_summary.tsv",
    params: runs=RAW + "/illumina/runs.tsv", results=RES + "/illumina"
    shell: "python scripts/summarize_illumina.py {params.runs} labels.tsv {params.results} {output.composition} {output.label} {output.qc}"


rule nanopore_filter:
    input: RAW + "/{dataset}/{run}_1.fastq.gz"
    output: RES + "/{dataset}/filtered/{run}.fastq.gz"
    shell:
        "chopper -q {config[nanopore_qc][min_quality]} -l {config[nanopore_qc][min_length]} "
        "--maxlength {config[nanopore_qc][max_length]} -i {input} 2> /dev/null | "
        "seqkit sample -n {config[nanopore_qc][max_reads]} -s 1 2> /dev/null | gzip > {output}"


rule nanopore_stats:
    input: raw=RAW + "/{dataset}/{run}_1.fastq.gz", filtered=RES + "/{dataset}/filtered/{run}.fastq.gz"
    output: RES + "/{dataset}/stats/{run}.tsv"
    shell:
        "(nanoq -i {input.raw} -s -H 2> /dev/null | sed 's/^/raw\\t/'; "
        "nanoq -i {input.filtered} -s -H 2> /dev/null | sed 's/^/filtered\\t/') > {output}"


rule combined_reference:
    input: expand(REF + "/db/{marker}.fasta", marker=MARKERS)
    output: REF + "/db/all_markers.fasta"
    shell: "cat {input} > {output}"


rule minimap2:
    input: reads=RES + "/{dataset}/filtered/{run}.fastq.gz", ref=REF + "/db/all_markers.fasta"
    output: RES + "/{dataset}/map/{run}.paf"
    threads: 4
    benchmark: RES + "/benchmarks/minimap2_{dataset}_{run}.txt"
    shell: "minimap2 -x map-ont -N 20 --secondary=yes -c -t {threads} {input.ref} {input.reads} 2> /dev/null > {output}"


rule identify_reads:
    input: RES + "/{dataset}/map/{run}.paf"
    output: assign=RES + "/{dataset}/assign/{run}.tsv", hits=RES + "/{dataset}/assign/{run}.tsv.hits"
    shell: "python scripts/paf_to_hits.py {input} {output.hits} && python scripts/identify.py {output.hits} {output.assign}"


rule validate_nanopore:
    input:
        assign=expand(RES + "/nanopore_single_source/assign/{run}.tsv", run=NANO),
        stats=expand(RES + "/nanopore_single_source/stats/{run}.tsv", run=NANO),
    output:
        validation=RES + "/nanopore/validation.tsv",
        sensitivity=RES + "/nanopore/sensitivity.tsv",
        qc=RES + "/nanopore/qc_summary.tsv",
    params: runs=RAW + "/nanopore_single_source/runs.tsv", results=RES + "/nanopore_single_source"
    shell: "python scripts/validate_nanopore.py {params.runs} {params.results} {output.validation} {output.sensitivity} {output.qc}"


rule mock_eval:
    input: expand(RES + "/nanopore_mock/assign/{run}.tsv", run=MOCK)
    output: RES + "/mock/mock_eval.tsv"
    params: runs=RAW + "/nanopore_mock/runs.tsv", results=RES + "/nanopore_mock"
    shell: "python scripts/mock_eval.py {params.runs} mock_truth.tsv {params.results} {output}"
