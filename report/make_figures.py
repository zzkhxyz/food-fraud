import csv
import gzip
import sys
from collections import Counter, defaultdict
from itertools import islice
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "report/figures")
CONFIG = yaml.safe_load(open("config.yaml"))
SAMPLE_READS = 20000
TOP_GENERA = 9
COLORS = ["#0071e3", "#ff9f0a", "#30b158", "#ff375f", "#af52de", "#64d2ff", "#a2845e", "#ffd60a", "#5e5ce6"]
GREY = "#c7c7cc"
OK, GENUS, BAD, NOTE = "#248a3d", "#0071e3", "#d70015", "#b25000"

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "savefig.dpi": 200})


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / f"{name}.png")


def genus(name):
    return name.split(" ")[0]


def pipeline_figure():
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.axis("off")
    boxes = {
        "BOLD v5\nCOI barcodes": (0.08, 0.85), "NCBI RefSeq\nmitogenomes": (0.08, 0.55),
        "Reference\n4 markers": (0.3, 0.7),
        "Illumina 2x125\n20 products": (0.08, 0.2), "fastp, merge,\nUNOISE": (0.3, 0.2), "blastn\n(16S)": (0.52, 0.2),
        "Nanopore\n17 truth + 10 mock": (0.08, -0.1), "chopper,\nsubsample": (0.3, -0.1), "minimap2\nmap-ont": (0.52, -0.1),
        "Identify\nid 97 / cov 90 / margin 2": (0.76, 0.05),
        "Label vs DNA": (0.95, 0.4), "Validation +\nsensitivity": (0.95, 0.05), "Mock\nevaluation": (0.95, -0.3),
    }
    for text, (x, y) in boxes.items():
        color = "#e8f1fb" if "Identify" not in text else "#1d1d1f"
        fc = "#1d1d1f" if "Identify" in text else "#1d1d1f"
        ax.text(x, y, text, ha="center", va="center", fontsize=7.5, color="white" if "Identify" in text else fc,
                bbox=dict(boxstyle="round,pad=0.45", fc=color, ec="#86868b", lw=0.6), transform=ax.transAxes)
    arrows = [((0.08, 0.85), (0.3, 0.7)), ((0.08, 0.55), (0.3, 0.7)), ((0.08, 0.2), (0.3, 0.2)), ((0.3, 0.2), (0.52, 0.2)),
              ((0.08, -0.1), (0.3, -0.1)), ((0.3, -0.1), (0.52, -0.1)), ((0.3, 0.7), (0.52, 0.2)), ((0.3, 0.7), (0.52, -0.1)),
              ((0.52, 0.2), (0.76, 0.05)), ((0.52, -0.1), (0.76, 0.05)),
              ((0.76, 0.05), (0.95, 0.4)), ((0.76, 0.05), (0.95, 0.05)), ((0.76, 0.05), (0.95, -0.3))]
    for (x1, y1), (x2, y2) in arrows:
        end = 0.11 if x2 == 0.76 else 0.07
        start = 0.11 if x1 == 0.76 else 0.07
        ax.annotate("", xy=(x2 - end, y2), xytext=(x1 + start, y1), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="#86868b", lw=0.8))
    ax.set_ylim(-0.4, 1.0)
    save(fig, "fig1_pipeline")


def reference_figure():
    stats = [r for r in read(RESULTS / "reference/reference_stats.tsv") if r["marker"] in ("COI", "16S", "12S", "CYTB")]
    cross = Counter(r["status"] for r in read(RESULTS / "reference/cross_check.tsv"))
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.5, 2.8), gridspec_kw={"width_ratios": [1.3, 1]})
    markers = [r["marker"] for r in stats]
    bold = [int(r["from_BOLD"]) for r in stats]
    refseq = [int(r["from_RefSeq"]) for r in stats]
    a.bar(markers, bold, color=COLORS[0], label="BOLD")
    a.bar(markers, refseq, bottom=bold, color=COLORS[1], label="RefSeq")
    a.set_ylabel("reference sequences")
    a.set_xlabel("marker")
    a.set_title("A. Reference size by marker and source")
    a.legend(frameon=False)
    order = ["agree", "different species, same genus", "different genus"]
    values = [cross.get(k, 0) for k in order]
    b.barh(["same species", "other species,\nsame genus", "other genus"], values, color=[OK, NOTE, BAD])
    for i, v in enumerate(values):
        b.text(v + 3, i, str(v), va="center")
    b.invert_yaxis()
    b.set_xlabel("RefSeq COI sequences")
    b.set_title("B. Best BOLD match of each RefSeq COI")
    save(fig, "fig2_reference")


def illumina_qc_figure():
    qc = read(RESULTS / "illumina/qc_summary.tsv")
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.5, 4.2), sharex=True)
    x = np.arange(len(qc))
    a.bar(x, [int(r["raw_reads"]) / 1e6 for r in qc], color=GREY, label="raw")
    a.bar(x, [int(r["after_fastp"]) / 1e6 for r in qc], color=COLORS[0], width=0.5, label="after fastp")
    a.set_ylabel("reads (millions)")
    a.set_title("A. Reads per product before and after quality filtering")
    a.legend(frameon=False)
    b.bar(x, [100 * float(r["merge_rate"]) for r in qc], color=COLORS[2])
    b.axhline(80, color="#86868b", lw=0.6, ls="--")
    b.set_ylabel("pairs merged (%)")
    b.set_ylim(0, 105)
    b.set_title("B. Share of read pairs merged into one amplicon")
    b.set_xticks(x, [r["run"].replace("SRR160886", "…") for r in qc], rotation=90, fontsize=7)
    b.set_xlabel("sequencing run (SRR160886..)")
    save(fig, "fig3_illumina_qc")


def read_lengths(path, limit):
    lengths, quals = [], []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        for i, line in enumerate(islice(f, limit * 4)):
            if i % 4 == 1:
                lengths.append(len(line.strip()))
            if i % 4 == 3:
                q = [ord(c) - 33 for c in line.strip()]
                quals.append(-10 * np.log10(np.mean([10 ** (-v / 10) for v in q])))
    return lengths, quals


def platform_figure():
    ill_files = sorted((RESULTS / "illumina/merged").glob("*.merged.fastq"))
    nano_files = sorted((RESULTS / "nanopore_single_source/filtered").glob("*.fastq.gz"))
    ill_len, ill_q = read_lengths(ill_files[0], SAMPLE_READS)
    nano_len, nano_q = [], []
    for f in nano_files[:3]:
        l, q = read_lengths(f, SAMPLE_READS // 3)
        nano_len += l
        nano_q += q
    ill_id = [float(r["top_identity"]) for f in (RESULTS / "illumina/assign").glob("*.tsv") for r in read(f)]
    nano_id = [float(r["top_identity"]) for f in (RESULTS / "nanopore_single_source/assign").glob("*.tsv") for r in read(f)]
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.6))
    axes[0].hist(ill_len, bins=np.arange(60, 300, 4), color=COLORS[0], alpha=0.8, label="Illumina merged", density=True)
    axes[0].hist(nano_len, bins=np.arange(60, 300, 4), color=COLORS[1], alpha=0.7, label="Nanopore", density=True)
    axes[0].set_yscale("log")
    axes[0].set_xlabel("read length (bp)")
    axes[0].set_ylabel("density (log)")
    axes[0].set_title("A. Length")
    axes[0].legend(frameon=False, fontsize=7)
    axes[1].hist(ill_q, bins=np.arange(5, 42, 1), color=COLORS[0], alpha=0.8, density=True)
    axes[1].hist(nano_q, bins=np.arange(5, 42, 1), color=COLORS[1], alpha=0.7, density=True)
    axes[1].set_xlabel("mean read quality (Phred)")
    axes[1].set_ylabel("density")
    axes[1].set_title("B. Quality")
    bins = np.arange(80, 100.5, 0.5)
    axes[2].hist(ill_id, bins=bins, color=COLORS[0], alpha=0.8, density=True)
    axes[2].hist(nano_id, bins=bins, color=COLORS[1], alpha=0.7, density=True)
    axes[2].axvline(CONFIG["thresholds"]["min_identity"], color=BAD, lw=1, ls="--")
    axes[2].text(CONFIG["thresholds"]["min_identity"] - 0.3, axes[2].get_ylim()[1] * 0.9, "species\nthreshold",
                 ha="right", fontsize=7, color=BAD)
    axes[2].set_xlabel("identity to best reference (%)")
    axes[2].set_ylabel("density")
    axes[2].set_title("C. Identity of best hit")
    save(fig, "fig4_platforms")


def composition_figure():
    label = read(RESULTS / "illumina/label_vs_content.tsv")
    comp = defaultdict(lambda: defaultdict(float))
    for r in read(RESULTS / "illumina/composition.tsv"):
        key = "unassigned" if r["taxon"] == "unassigned" else genus(r["taxon"])
        comp[r["run"]][key] += float(r["fraction"])
    weight = defaultdict(float)
    for parts in comp.values():
        for g, v in parts.items():
            if g != "unassigned":
                weight[g] += v
    top = sorted(weight, key=weight.get, reverse=True)[:TOP_GENERA]
    fig, ax = plt.subplots(figsize=(7.5, 5.4))
    verdict_color = {"label confirmed": OK, "label not confirmed": BAD, "label not specific": NOTE}
    names = []
    for i, r in enumerate(label):
        left = 0
        parts = comp[r["run"]]
        for j, g in enumerate(top):
            ax.barh(i, parts.get(g, 0), left=left, color=COLORS[j], height=0.72, label=g if i == 0 else None)
            left += parts.get(g, 0)
        other = sum(v for g, v in parts.items() if g not in top and g != "unassigned")
        ax.barh(i, other, left=left, color="#636366", height=0.72, label="other genera" if i == 0 else None)
        left += other
        ax.barh(i, parts.get("unassigned", 0), left=left, color=GREY, height=0.72, label="unassigned" if i == 0 else None)
        declared = "fish" if r["declared"] == "fish" else r["declared"]
        names.append(f"{r['product']}  [{declared}]")
    ax.set_yticks(range(len(label)), names, fontsize=7.5)
    for tick, r in zip(ax.get_yticklabels(), label):
        tick.set_color(verdict_color[r["verdict"]])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of reads")
    ax.set_title("Genus composition of every product (label colour: green confirmed, red not confirmed, orange no species named)")
    ax.legend(ncol=4, frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.4, -0.08))
    save(fig, "fig5_composition")


def truth_figure():
    rows = read(RESULTS / "nanopore/validation.tsv")
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    x = np.arange(len(rows))
    res_color = {"correct species": OK, "correct genus": GENUS, "wrong": BAD}
    total = [int(r["reads_assigned"]) for r in rows]
    sp = [int(r["species_level"]) / t for r, t in zip(rows, total)]
    ge = [int(r["genus_level"]) / t for r, t in zip(rows, total)]
    ax.bar(x, sp, color=COLORS[2], label="species-level reads")
    ax.bar(x, ge, bottom=sp, color=COLORS[0], label="genus-level reads")
    ax.bar(x, [1 - a - b for a, b in zip(sp, ge)], bottom=[a + b for a, b in zip(sp, ge)], color=GREY, label="unassigned reads")
    for i, r in enumerate(rows):
        ax.text(i, 1.03, "●", ha="center", color=res_color[r["result"]], fontsize=9)
    ax.set_xticks(x, [r["sample"].split(" - ")[0].replace(" processed tissue", " (proc.)").replace(" tissue", "")[:22] for r in rows],
                  rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("share of reads")
    ax.set_ylim(0, 1.1)
    ax.set_title("Nanopore truth set: read calls per sample (dot: green species, blue genus, red wrong)", pad=28)
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.08))
    save(fig, "fig6_truth_set")


def sensitivity_figure():
    rows = read(RESULTS / "nanopore/sensitivity.tsv")
    idents = sorted({int(r["min_identity"]) for r in rows})
    margins = sorted({int(r["min_margin"]) for r in rows})
    grid = np.zeros((len(idents), len(margins)))
    species = np.zeros_like(grid)
    for r in rows:
        i, j = idents.index(int(r["min_identity"])), margins.index(int(r["min_margin"]))
        grid[i, j] = 100 * float(r["false_id_rate"])
        species[i, j] = int(r["correct_species"])
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.5, 3.0))
    for ax, data, title, cmap, fmt in ((a, grid, "A. False identification rate (%)", "Reds", "{:.0f}"),
                                       (b, species, "B. Correct species calls (of 17)", "Greens", "{:.0f}")):
        im = ax.imshow(data, cmap=cmap, aspect="auto")
        ax.set_xticks(range(len(margins)), [f"≥{m}" for m in margins])
        ax.set_yticks(range(len(idents)), [f"≥{i}%" for i in idents])
        ax.set_xlabel("margin to second species (points)")
        ax.set_ylabel("minimum identity")
        ax.set_title(title)
        for i in range(len(idents)):
            for j in range(len(margins)):
                ax.text(j, i, fmt.format(data[i, j]), ha="center", va="center", fontsize=7,
                        color="white" if data[i, j] > data.max() * 0.6 else "black")
        ci = idents.index(CONFIG["thresholds"]["min_identity"])
        cj = margins.index(CONFIG["thresholds"]["min_margin_to_second"])
        ax.add_patch(plt.Rectangle((cj - 0.5, ci - 0.5), 1, 1, fill=False, ec="black", lw=1.6))
        fig.colorbar(im, ax=ax, shrink=0.8)
    save(fig, "fig7_sensitivity")


def mock_figure():
    rows = read(RESULTS / "mock/mock_eval.tsv")
    genera = sorted({genus(s) for r in rows for s in r["expected"].split("; ")})
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    for i, r in enumerate(rows):
        expected = {genus(s) for s in r["expected"].split("; ")}
        detected = {d.split(" (")[0] for d in r["detected_genus"].split("; ") if d}
        for j, g in enumerate(genera):
            if g in expected and g in detected:
                color, mark = OK, "●"
            elif g in expected:
                color, mark = BAD, "○"
            elif g in detected:
                color, mark = NOTE, "×"
            else:
                continue
            ax.text(i, j, mark, ha="center", va="center", color=color, fontsize=13)
        ax.text(i, len(genera) - 0.35, f"{int(r['assigned_reads']):,}", ha="center", fontsize=6.5, color="#6e6e73")
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylim(len(genera) - 0.1, -0.6)
    ax.set_xticks(range(len(rows)), [r["sample"] for r in rows], rotation=35, ha="right", fontsize=7)
    ax.set_yticks(range(len(genera)), genera, fontstyle="italic")
    ax.set_xlabel("mock mixture (number: assigned reads)")
    ax.set_title("Mock mixtures at genus level: ● expected and found, ○ expected but missed, × found but not expected")
    ax.grid(True, color="#e5e5ea", lw=0.5)
    ax.set_axisbelow(True)
    save(fig, "fig8_mock")


if __name__ == "__main__":
    pipeline_figure()
    reference_figure()
    illumina_qc_figure()
    platform_figure()
    composition_figure()
    truth_figure()
    sensitivity_figure()
    mock_figure()
