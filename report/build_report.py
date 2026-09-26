import csv
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RESULTS = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
FIGURES = Path("report/figures")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "report/Food_Fraud_Report.docx")
FONT = "Calibri"
CODE_FONT = "Consolas"
INK = RGBColor(0x1D, 0x1D, 0x1F)
MUTED = RGBColor(0x6E, 0x6E, 0x73)
HEADER_FILL = "E8EEF6"

fig_no = 0
tab_no = 0


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))


def shade(cell, color):
    props = cell._tc.get_or_add_tcPr()
    fill = OxmlElement("w:shd")
    fill.set(qn("w:val"), "clear")
    fill.set(qn("w:color"), "auto")
    fill.set(qn("w:fill"), color)
    props.append(fill)


def add_runs(par, text):
    for i, chunk in enumerate(text.split("`")):
        if i % 2 == 1:
            run = par.add_run(chunk)
            run.font.name = CODE_FONT
            run.font.size = Pt(9)
            continue
        for j, part in enumerate(chunk.split("*")):
            if part:
                run = par.add_run(part)
                run.italic = j % 2 == 1


def p(doc, text, space=6):
    par = doc.add_paragraph()
    add_runs(par, text)
    par.paragraph_format.space_after = Pt(space)
    return par


def bullets(doc, items):
    for item in items:
        par = doc.add_paragraph(style="List Bullet")
        add_runs(par, item)
        par.paragraph_format.space_after = Pt(2)


def figure(doc, name, caption, width=16):
    global fig_no
    fig_no += 1
    doc.add_picture(str(FIGURES / f"{name}.png"), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    run = cap.add_run(f"Figure {fig_no}. ")
    run.bold = True
    run.font.size = Pt(9)
    run = cap.add_run(caption)
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED
    cap.paragraph_format.space_after = Pt(10)


def table(doc, rows, caption, widths=None, size=9):
    global tab_no
    tab_no += 1
    cap = doc.add_paragraph()
    run = cap.add_run(f"Table {tab_no}. ")
    run.bold = True
    run.font.size = Pt(9)
    run = cap.add_run(caption)
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED
    cap.paragraph_format.space_after = Pt(3)
    cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            add_runs(cell.paragraphs[0], str(value))
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(size)
                run.bold = i == 0 or run.bold
            if i == 0:
                shade(cell, HEADER_FILL)
            if widths:
                cell.width = Cm(widths[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def setup():
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(section, side, Cm(2.2))
    section.top_margin = section.bottom_margin = Cm(2)
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(10.5)
    style.font.color.rgb = INK
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    for level, size in ((1, 15), (2, 12)):
        h = doc.styles[f"Heading {level}"]
        h.font.name = FONT
        h.font.size = Pt(size)
        h.font.color.rgb = INK
        h.font.bold = True
        h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
        h.paragraph_format.space_after = Pt(4)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.text = text
        run._r.append(el)
    return doc


def title(doc):
    par = doc.add_paragraph()
    run = par.add_run("Food Fraud: Is the Label Telling the Truth?")
    run.bold = True
    run.font.size = Pt(22)
    par.paragraph_format.space_after = Pt(2)
    par = doc.add_paragraph()
    run = par.add_run("DNA barcoding of processed seafood with Illumina and Nanopore data")
    run.font.size = Pt(13)
    run.font.color.rgb = MUTED
    meta = [
        "Zhan Tabuldinov, BDA-2401",
        "Introduction to Bioinformatics, Course Project 04, Astana IT University, 2026",
        "Code: github.com/zzkhxyz/food-fraud    Results dashboard: food-fraud.vercel.app",
    ]
    for line in meta:
        par = doc.add_paragraph()
        run = par.add_run(line)
        run.font.size = Pt(10)
        par.paragraph_format.space_after = Pt(0)
    doc.add_paragraph()
    box = doc.add_table(rows=1, cols=1)
    box.style = "Table Grid"
    cell = box.cell(0, 0)
    shade(cell, "F5F5F7")
    cell.text = ""
    run = cell.paragraphs[0].add_run("Summary. ")
    run.bold = True
    add_runs(cell.paragraphs[0],
             "I read the DNA of 20 processed seafood products bought in Italian shops and compared it with the label. "
             "All four products that name a species or genus on the label (two tuna burgers, a swordfish burger and a sea bass "
             "burger) contain that fish. One product, a salmon burger, could not be identified, because the reference database "
             "has too few salmon sequences for this marker. The other 15 products only say “fish”. Fish sticks and nuggets are "
             "made of cod-family fish (*Gadus*), but most surimi products are made of cheap small pelagic fish such as sardinella, "
             "mackerel and anchovy, not the Alaska pollock a buyer would expect. The method was tested on 17 control samples of "
             "known species: it finds the right genus in 12 of 17 cases, but it rarely separates close species inside a genus. "
             "So the evidence is strong at genus level and weak at species level, and I state this for every product.")
    doc.add_paragraph()


def framing(doc):
    doc.add_heading("1. Problem and biological framing", 1)
    p(doc, "Seafood is one of the most frequently mislabelled foods. Market surveys in Europe and North America regularly find "
           "that a noticeable share of fish sold under one name is another, usually cheaper, species. The risk is not only "
           "economic: a substituted species can carry an allergen, a toxin or come from an endangered or illegally caught stock. "
           "Once fish is filleted, breaded, minced into a burger or pressed into surimi, its shape, skin and bones are gone, and "
           "nobody can recognise the species by eye. A consumer protection agency therefore needs a laboratory method that reads "
           "the species from the product itself, and that gives an answer strong enough to defend in court.")
    doc.add_heading("1.1 DNA barcoding", 2)
    p(doc, "DNA barcoding identifies a species from a short, standard piece of its DNA. For animals the classic barcode is a "
           "650 bp region of the mitochondrial gene *COI* (cytochrome c oxidase subunit I). It works for three reasons. First, "
           "a cell holds hundreds to thousands of copies of mitochondrial DNA, so enough DNA survives cooking and processing. "
           "Second, *COI* changes fast enough that different species usually differ by more than 2–3%, while individuals of one "
           "species usually differ by less than 1%. Third, the BOLD Systems library holds millions of reference barcodes, so a "
           "sequence from a product can be compared with known species.")
    p(doc, "Barcoding also fails in known ways, and these limit what a result can mean:")
    bullets(doc, [
        "*Young species groups.* Species that separated recently, such as the tunas (*Thunnus*) or the Pacific salmons "
        "(*Oncorhynchus*), can share almost the same barcode. A single marker then identifies the genus, not the species.",
        "*Maternal inheritance and hybrids.* Mitochondria come only from the mother. A hybrid fish looks like its mother's "
        "species, and gene flow between species (introgression) can move one species' mitochondria into another.",
        "*NUMTs.* Copies of mitochondrial genes inside the nuclear genome can be amplified by mistake and give a false signal.",
        "*Processing.* Heat and pressure break DNA into short fragments. In heavily processed food the full 650 bp barcode is "
        "often gone, so studies amplify shorter “mini-barcodes” of 100–250 bp, often from *16S* or *12S* rRNA genes, which carry "
        "less information.",
        "*Reference gaps and errors.* A species can only be named if it is in the reference, and reference records themselves "
        "sometimes carry the wrong name.",
    ])
    p(doc, "So a barcode result means “this DNA is most similar to the reference sequences of species X”. It becomes a species "
           "identification only when the match is close, covers the read, and is clearly better than the next species. This "
           "project makes those three conditions explicit and measures how often they give the right answer.")
    doc.add_heading("1.2 Question and why these data can answer it", 2)
    p(doc, "The question is: for each product, does the fish DNA agree with the fish on the label, and how sure can we be? "
           "To answer it I need (a) sequence data from real market products, (b) control samples where the true species is "
           "known, so that the error rate can be measured, and (c) a reference that covers commercial fish. The chosen data "
           "give all three: an Illumina metabarcoding study of 20 real products, a Nanopore study of single-species samples, "
           "and Nanopore mixtures of known composition, plus a reference built from BOLD and NCBI RefSeq.")


def data_section(doc):
    doc.add_heading("2. Data sources", 1)
    p(doc, "All data are public. Nothing was downloaded by hand: every file is fetched by a script, and every read file is "
           "checked with the MD5 sum published by the European Nucleotide Archive (ENA). All sources were retrieved on "
           "11 September 2026.")
    table(doc, [
        ["Role", "Accession / source", "Platform", "Content", "Used"],
        ["Market products", "PRJNA766222 (SRR16088612–631)", "Illumina NextSeq 500, 2×125 bp",
         "20 processed seafood products, mitochondrial 16S amplicon", "20 runs, 318 MB"],
        ["Truth set", "PRJNA1272083 (SRR33832769, SRR33849502–516, 585, 586)", "Oxford Nanopore MinION",
         "single-species animal tissue, four mitochondrial mini-barcodes", "17 fish and prawn runs, 199 MB"],
        ["Mock mixtures", "PRJEB39300 (ERR4405444–451, 461, 467)", "Oxford Nanopore MinION",
         "cod, haddock, whiting and wolffish mixed in known proportions", "10 of the runs, 209 MB"],
        ["COI reference", "BOLD Systems v5 API", "–", "COI barcodes of 19 commercial families", "54,112 records"],
        ["Mitogenome reference", "NCBI RefSeq via Entrez", "–",
         "complete mitochondrial genomes of fish, sharks, lampreys, crustaceans, molluscs", "about 5,100 genomes"],
    ], "Every dataset used, with accessions, platform and size.", widths=[2.4, 4.2, 2.8, 4.6, 2.6], size=8.5)
    doc.add_heading("2.1 Identifier mapping and metadata problems", 2)
    p(doc, "Several identifier systems had to be connected, and several metadata problems had to be solved:")
    bullets(doc, [
        "*BioProject to runs.* A BioProject number (PRJNA…) does not point to files. The ENA portal API returns the run table "
        "for each project with sample title, library name, read count and MD5, and the scripts work from this table.",
        "*Runs to products.* In PRJNA766222 the product is written only in the library name, for example “10_Salmon burger”. "
        "I built a table (`labels.tsv`) that maps each library name to the product, the declared taxon and the rank of the "
        "claim (species, genus, or none for “fish”).",
        "*Mock composition.* In PRJEB39300 the species in a mixture appear only as common names in the sample title "
        "(for example “Cod, Haddock, Whiting”). These are mapped to scientific names with `mock_truth.tsv`.",
        "*BOLD API change.* The old BOLD v4 API no longer answers. The v5 API needs a User-Agent header and returns nothing "
        "for class-level queries, so the reference is downloaded family by family (19 families).",
        "*Inconsistent names.* BOLD records without a real species name (“sp.”, codes), hybrids and sequences shorter than "
        "400 bp were removed. In RefSeq the same gene is annotated as COX1, CO1, COI or COXI, and 16S rRNA also as “l-rRNA”; "
        "all variants are recognised when the four markers are cut out of each genome.",
    ])
    doc.add_heading("2.2 Disagreement between BOLD and RefSeq", 2)
    p(doc, "To test the two sources against each other, every RefSeq *COI* sequence (4,918) was searched with BLAST against the "
           "whole *COI* reference, keeping the five best hits. For the 508 sequences whose five best hits include a BOLD record, "
           "the best BOLD match was compared with the RefSeq name (Figure 2B): 287 (56%) name the same species in both databases, "
           "64 (13%) name another species of the same genus, and 157 (31%) name a different genus. The last group probably consists "
           "mostly of species that have no BOLD record in my 19 families, so their nearest BOLD neighbour is only a relative; the "
           "middle group is the real naming conflict. My rule for resolving conflicts is simple and written in "
           "the code: both sources stay in the reference, the best hit per species is taken, and a species is named only if it "
           "beats the second species by at least 2 identity points. If two names tie, the call falls back to the genus. In this "
           "way a disagreement between databases produces a less precise answer, never a confident wrong species.")


def approach(doc):
    doc.add_heading("3. Choice of approach and platforms", 1)
    p(doc, "Three laboratory strategies can identify fish in food. Table 2 compares them with approximate 2025 list prices "
           "(order of magnitude, including library preparation and a share of a sequencing run).")
    table(doc, [
        ["Strategy", "Cost per sample", "What it can detect", "Main weakness for food fraud"],
        ["Barcoding (PCR + Sanger)", "≈ $8–15", "one dominant species per sample",
         "mixed products give an unreadable trace; needs the long 650 bp barcode"],
        ["Metabarcoding (PCR + Illumina)", "≈ $20–40 at 96 samples per run", "every species above ≈1% of the DNA",
         "PCR can favour some species; short marker, often genus only"],
        ["Metabarcoding (PCR + Nanopore)", "≈ $10–30 with 24–96 barcodes", "mixtures; fast, portable, same day",
         "≈5% error per read at the quality seen here"],
        ["Shotgun (no PCR)", "≈ $50–150 for 5–10 Gb", "everything, without PCR bias",
         "only ≈0.1–1% of reads are mitochondrial; weak reference for whole genomes"],
    ], "Barcoding, metabarcoding and shotgun sequencing compared for seafood authentication.", widths=[3.4, 3.2, 4.3, 5.7], size=8.5)
    p(doc, "The decision can be made with numbers. To see a component that makes up 1% of a product with at least 10 reads, a "
           "sample needs about 1,000 reads from the barcode region. Metabarcoding puts almost all reads on the barcode: the 20 "
           "products here have between 3,924 and 1.66 million reads after filtering (median 366,728), far more than needed. With "
           "shotgun sequencing, where perhaps 0.5% of reads are mitochondrial and only a part of those fall on one marker, the same "
           "1,000 reads would require several million reads per sample, at five to ten times the cost. Sanger barcoding is the "
           "cheapest, but surimi is a mixture by design, and a mixture cannot be read from one Sanger trace. For processed and "
           "mixed products metabarcoding is therefore the right choice, which is also what the published studies used.")
    p(doc, "The two sequencing platforms shape the data in different ways (Figure 4). Illumina reads are short (2×125 bp) but "
           "very accurate: the mean share of bases with quality ≥ Q30 (at most one error in 1,000 bases) is 87% before and 89% "
           "after trimming. Because the 16S amplicon is about 207 bp long, the two reads of a pair overlap and can be merged into "
           "one full-length, error-corrected fragment. Nanopore reads cover the whole mini-barcode in one read (median length "
           "151 bp) and the run gives results in hours on a portable device, but the median read quality is about Q13, which "
           "means about 5% of bases are wrong. This single fact decides how far each platform can go: a species call needs 97% "
           "identity, which a 5%-error read can rarely reach on its own (Figure 4C).")


def methods(doc):
    doc.add_heading("4. Methods", 1)
    figure(doc, "fig1_pipeline", "The workflow. Both platforms are processed separately and then pass the same identification rules.")
    doc.add_heading("4.1 Illumina: quality control, merging and denoising", 2)
    p(doc, "Every threshold has a reason:")
    bullets(doc, [
        "*fastp, quality Q20 and tail trimming.* Q20 means a 1% error chance per base. Bases below it at the read ends are "
        "removed because they cause failed merges and false variants. This removed 3.6% of reads.",
        "*Minimum length 100 bp.* The reads are 125 bp and the pairs must overlap across a 207 bp amplicon; a read shorter than "
        "100 bp after trimming cannot reach the overlap.",
        "*vsearch merging, overlap ≥ 20 bp, ≤ 5 differences.* The expected overlap is about 40 bp, so 20 bp is a safe minimum; "
        "allowing five differences keeps pairs with a few sequencing errors in the overlap, which the merge then corrects.",
        "*Expected errors ≤ 1.* After merging, reads with more than one expected error in total are removed before denoising.",
        "*UNOISE denoising, minimum size 8, then chimera removal.* Illumina amplicon data contain two typical artefacts: "
        "rare error variants of real sequences, and chimeras formed when PCR joins two templates. UNOISE keeps only sequences "
        "seen at least 8 times that are not explained as errors of a more abundant sequence, and UCHIME3 removes chimeras. "
        "The result is 2 to 76 exact sequence variants (ASVs) per product.",
    ])
    doc.add_heading("4.2 Nanopore: filtering and mapping", 2)
    p(doc, "Reads were kept if they were 80–2,000 bp long and had a mean quality of Q10 or more (chopper). The lower length "
           "limit removes adapter-only fragments; the upper limit removes chimeric reads, since the mini-barcodes are about 150 bp. "
           "Q10 removes the worst reads (more than 10% errors) but keeps most data, because stricter filtering would throw away "
           "reads without making them good enough for species calls. Runs larger than 20,000 reads were randomly subsampled to "
           "20,000 with a fixed seed to limit run time; this is a deliberate choice and is listed as a limitation.")
    p(doc, "Illumina ASVs are compared with the 16S reference by *blastn*. BLAST is a local aligner: it finds short exact seeds, "
           "extends them without gaps and then with gaps, and reports percent identity, alignment length and query coverage. "
           "It is sensitive and gives exact identity values, which is what the thresholds need. Nanopore reads are instead "
           "mapped with *minimap2* in the `map-ont` preset, which uses minimizer seeds and chaining and is tuned for the "
           "insertion and deletion errors typical of Nanopore. Running BLAST on hundreds of thousands of noisy reads would be much "
           "slower. Minimap2 is run against all four markers at once and keeps up to 20 alternative hits per read, so that ties "
           "between species are visible to the identification step.")
    doc.add_heading("4.3 Identification rules", 2)
    p(doc, "Each ASV or read gets one of three answers, using the best hit of each species:")
    bullets(doc, [
        "*Species*, if identity ≥ 97%, query coverage ≥ 90%, and the best species leads the second-best species by ≥ 2 points.",
        "*Genus*, if identity is between 90% and 97%, or if another species of the same genus is within 2 points.",
        "*Unassigned* in all other cases, including when two different genera tie.",
    ])
    p(doc, "The 97% threshold is the usual species boundary for animal barcodes; 90% coverage prevents a short partial match "
           "from counting as an identification; the 2-point margin reflects that close species often differ by only 1–2%. "
           "Because these numbers are conventions, Section 5.3 measures how the error rate changes when they change.")
    doc.add_heading("4.4 Engineering and reproducibility", 2)
    p(doc, "The whole analysis is a Snakemake workflow of 204 jobs that runs inside a Docker image with all tools installed from "
           "Bioconda at fixed versions. One command, `docker compose run --rm pipeline`, reproduces every table from the raw "
           "reads, and a 1.5 MB test set checks the workflow in minutes. Reads are streamed from compressed files through the "
           "filters and aligners, never loaded into memory. Run time and memory of every job were recorded (Table 3); the largest "
           "memory use was 1.2 GB for fastp, well inside a 4 GB Docker limit, and the whole analysis needs about 25 minutes of "
           "computing time on a laptop.")
    table(doc, [
        ["Step", "Jobs", "Total time", "Peak memory"],
        ["fastp (Illumina QC)", "20", "170 s", "1.2 GB"],
        ["vsearch merge + denoise", "20", "486 s", "23 MB"],
        ["blastn (Illumina ASVs)", "20", "37 s", "98 MB"],
        ["minimap2 (Nanopore)", "27", "617 s", "451 MB"],
        ["BOLD vs RefSeq cross-check", "1", "177 s", "164 MB"],
    ], "Measured run time and memory per workflow step (8 CPU cores).", widths=[6, 2, 3, 3])


def results(doc):
    doc.add_heading("5. Results", 1)
    doc.add_heading("5.1 Reference database", 2)
    p(doc, "The final reference holds 29,200 *COI* sequences of 5,813 species (24,282 from BOLD, 4,918 from RefSeq) and about "
           "4,900 sequences each for *16S*, *12S* and *CYTB*, all from RefSeq (Figure 2A). The *16S* reference is therefore six "
           "times smaller than the *COI* reference, and this matters, because the market products were sequenced at *16S*.")
    figure(doc, "fig2_reference", "A: reference sequences per marker and source. B: for each RefSeq COI sequence, whether its best "
                                  "BOLD match names the same species, another species of the same genus, or another genus.")
    doc.add_heading("5.2 Data quality", 2)
    p(doc, "All 20 Illumina runs passed quality control (Figure 3). Most runs have 170,000 to 800,000 reads; one surimi product "
           "(SRR16088621) has only 5,058 reads, which is still enough for its main components. In 19 of 20 runs 84–99% of pairs "
           "merged. One surimi run (SRR16088625) merged only 26% of pairs, probably because part of its amplicons are longer than "
           "the 250 bp the two reads can span; its composition rests on fewer reads and should be read with more caution.")
    figure(doc, "fig3_illumina_qc", "Illumina quality control per product. A: reads before and after fastp. B: share of pairs "
                                    "merged; the dashed line marks 80%.")
    figure(doc, "fig4_platforms", "Illumina and Nanopore compared. A: read length (Illumina: merged fragments of one run; "
                                  "Nanopore: filtered reads of three runs). B: mean read quality. C: identity of the best "
                                  "reference hit for all Illumina ASVs and all Nanopore reads; the red line is the species threshold.")
    p(doc, "Figure 4C shows the main platform effect. Half of the Illumina ASVs match their best reference at 99% or more and "
           "62% pass the 97% species threshold. Nanopore reads have a median identity of 95.6%, and only 31% of reads reach 97%, "
           "because each read carries its own sequencing errors. The long-read platform therefore gives full-length "
           "barcode coverage in one read, but on these short mini-barcodes this advantage does not compensate for the higher error. "
           "The honest consequence is that single Nanopore reads support genus calls, not species calls.")
    doc.add_heading("5.3 How accurate is the method? (truth set)", 2)
    val = read(RESULTS / "nanopore/validation.tsv")
    counts = {k: sum(r["result"] == k for r in val) for k in ("correct species", "correct genus", "wrong")}
    p(doc, f"On the 17 single-species Nanopore samples the pipeline gives {counts['correct species']} correct species call, "
           f"{counts['correct genus']} correct genus calls and {counts['wrong']} wrong calls (Figure 5). All five errors have "
           "the same pattern: the called taxon is supported by only 1–4% of reads, and more than 90% of reads are unassigned. "
           "Two of them are close relatives of the truth (skipjack tuna called as bonito *Sarda*, Arctic cod as *Gadus*), and the "
           "king prawn is called as an octopus genus because shrimp are poorly covered by the reference. These are weak calls "
           "rather than confident errors, and a rule that requires a minimum share of supporting reads would turn most of them "
           "into “no call”; however, it would also remove the correct call for Atlantic cod, which is supported by only 0.9% of reads.")
    figure(doc, "fig6_truth_set", "Nanopore truth set. Bars show the share of reads assigned at species level, genus level or not "
                                  "at all; the dot shows the final call against the known species.")
    p(doc, "Figure 6 shows how the false identification rate depends on the thresholds. As a baseline, a naive “best hit wins” "
           "rule (identity ≥ 90%, no margin) makes 9 correct species calls but is wrong in 35% of samples. The chosen setting "
           "(97%, margin 2) lowers the error to 29% but keeps only one species call. Raising identity to 99% gives the lowest "
           "error, 24%, but then no species is named at all. There is no setting that gives both many species calls and a low "
           "error: for single-read Nanopore data the defensible statement is the genus.")
    figure(doc, "fig7_sensitivity", "Sensitivity analysis on the truth set. A: false identification rate for each combination of "
                                    "minimum identity and margin. B: number of correct species calls. The black box is the setting "
                                    "used in the pipeline.")
    doc.add_heading("5.4 Can it see mixtures? (mock communities)", 2)
    p(doc, "Mixtures were evaluated at genus level, counting a genus as detected when it has at least 1% of reads (Figure 7). "
           "Five of the ten runs have thousands of assigned reads. In these five, 11 of 13 expected genera are found: the "
           "cod–haddock–whiting mixture and the cod–wolffish mixture are fully recovered, while the four-species silage sample "
           "shows cod and wolffish but misses the minor haddock and whiting. The single-species haddock and whiting runs “leak” "
           "27% and 13% of their assigned reads to the other two cod-family genera, which are very close relatives. The remaining "
           "five runs have only 2–12 assigned reads, too few to judge; this is a negative result about those runs, not about the "
           "method. In short, the pipeline reports several fish in one product, but a small component that is a close relative of "
           "the main fish can be missed or confused.")
    figure(doc, "fig8_mock", "Mock mixtures at genus level. Filled circles: expected and found; open circles: expected but missed; "
                             "crosses: found but not expected. Numbers show assigned reads per run.")
    doc.add_heading("5.5 Market products: label versus DNA", 2)
    figure(doc, "fig5_composition", "Genus composition of every product from Illumina reads. Product names are coloured by verdict; "
                                    "the declared taxon is shown in brackets.")
    p(doc, "Table 4 gives the verdict for each product and whether the evidence would survive a challenge. I consider evidence "
           "strong when the declared taxon is found at the rank the label claims, passes all three rules, and is the main DNA "
           "in the product.")
    label = read(RESULTS / "illumina/label_vs_content.tsv")
    top = {}
    for r in read(RESULTS / "illumina/composition.tsv"):
        if r["taxon"] != "unassigned" and (r["run"] not in top or float(r["fraction"]) > top[r["run"]][1]):
            top[r["run"]] = (r["taxon"], float(r["fraction"]))
    rows = [["Product", "Label", "Main identified fish", "Unassigned", "Verdict", "Would it survive challenge?"]]
    for r in label:
        taxon, share = top.get(r["run"], ("none", 0))
        declared = "“fish”" if r["declared"] == "fish" else f"*{r['declared']}*"
        verdict = r["verdict"].replace("label ", "")
        rows.append([r["product"], declared, f"*{taxon}* ({share:.0%})", f"{float(r['unassigned_fraction']):.0%}",
                     verdict, strength(r)])
    table(doc, rows, "Label versus DNA for all 20 products (Illumina, 16S).", widths=[3.4, 2.6, 3.4, 1.6, 1.8, 4.2], size=8)
    p(doc, "The four products with a named fish contain it. The swordfish burger and the sea bass burger pass the species rules; "
           "the two tuna burgers are *Thunnus* at genus level, which is exactly what the label claims (“tuna”), because the tuna "
           "species are too similar at this marker. One tuna burger also contains 1.3% *Gadus*, most likely carry-over in a "
           "factory that also processes cod. The salmon burger is the only negative result: 98% of its reads are unassigned and "
           "only 2% reach *Oncorhynchus*. This is best explained by the thin *16S* reference for salmonids, and the correct "
           "statement is “not confirmed”, not “substituted”.")
    p(doc, "The 15 products labelled only “fish” cannot be false by name, but their content tells a clear story. Breaded "
           "cutlets, nuggets and one fish-stick product are almost pure *Gadus*, as expected for white fish, and the second "
           "fish-stick product is 60% *Gadus* with the rest unassigned. Surimi is very different: in 6 "
           "of 10 surimi products the main DNA is not cod-family fish but *Sardinella*, *Scomber* or *Nematalosa*, three products "
           "are more than 75% *Sardinella*, and in two more the largest single part (30–34%) is unassigned DNA, followed by anchovy or snapper. "
           "The two “crab flavour” products and the “shrimp flavour” product contain no crustacean DNA, which fits the fact that "
           "the flavour is an additive. One “crab claw” product (SRR16088625) does contain a trace of real crab, the swimming "
           "crab *Portunus sanguinolentus*, at 0.5% of reads, perhaps from a small amount of crab meat or extract.")


def strength(r):
    if r["verdict"] == "label confirmed":
        return "Yes, at the rank the label claims"
    if r["verdict"] == "label not confirmed":
        return "No conclusion possible: reference gap"
    if float(r["unassigned_fraction"]) >= 0.5:
        return "No claim to test; content mostly unassigned"
    return "No claim to test; genus content is solid"


def limitations(doc):
    doc.add_heading("6. Limitations", 1)
    bullets(doc, [
        "*Reference gaps.* The *16S* reference is six times smaller than the *COI* reference. The salmon burger and the high "
        "unassigned share in some surimi products are the visible cost of this.",
        "*One short marker.* Market products were sequenced only at a ≈207 bp *16S* region, which often separates genera but "
        "not close species. A second marker (for example *COI* or *CYTB*) would be needed for species-level claims.",
        "*Per-read Nanopore identification.* With about 5% error per read, species calls would need a consensus sequence built "
        "from many reads. The pipeline does not build consensus sequences, so Nanopore results stay at genus level.",
        "*No minimum-support rule.* A call supported by 1–4% of reads is reported like any other call. All five truth-set errors "
        "are of this kind.",
        "*Proportions are not weights.* Read shares reflect DNA amount and PCR efficiency, not the weight of each fish in the "
        "product, so “95% Sardinella” does not mean 95% of the product mass.",
        "*Subsampling and small controls.* Nanopore runs were capped at 20,000 reads, and the truth set has only 17 samples, so "
        "the error rate of 29% has a wide confidence interval.",
        "*No ZymoBIOMICS control.* The handbook suggests a ZymoBIOMICS mock community, but it is a bacterial community and "
        "cannot test fish barcodes; the fish mock mixtures of PRJEB39300 were used instead.",
    ])


def conclusion(doc):
    doc.add_heading("7. Conclusion", 1)
    p(doc, "DNA barcoding can check seafood labels even after heavy processing. In this set of 20 Italian products, every product "
           "that names its fish contains that fish, and I found no hidden swap of an expensive species for a cheap one. The "
           "main finding is a lack of transparency: surimi labelled only as “fish” is mostly made of cheap small pelagic fish, "
           "not the Alaska pollock a buyer would expect. This is legal, but a buyer cannot know what they eat.")
    p(doc, "The measured error rates define how far the evidence goes. At genus level the method is reliable and the results "
           "would survive challenge; at species level, with one short marker and single Nanopore reads, they would not. For an "
           "enforcement case the pipeline should report the genus, the three rule values behind each call, and the validated error "
           "rate, and it should answer “not confirmed” instead of guessing when the reference is missing, as it did for the salmon "
           "burger. The next improvements are clear: a larger *16S* reference, a second marker, consensus calling for Nanopore "
           "reads, and a minimum-support rule.")


def appendix(doc):
    doc.add_heading("Contribution statement", 1)
    p(doc, "This is an individual project. Zhan Tabuldinov designed and carried out all parts of the work: the choice of datasets, "
           "data retrieval and the reference database, Illumina and Nanopore processing, the identification rules and sensitivity "
           "analysis, the Snakemake workflow and Docker environment, the results dashboard and this report.")
    doc.add_heading("Appendix A. Use of AI assistants", 1)
    p(doc, "I used Claude (Anthropic) through Claude Code as a coding and writing assistant: to help write and debug the Python "
           "scripts and Snakemake rules, to find and fix parsing bugs in the summary scripts, to build the web dashboard and the "
           "figure scripts, and to edit the English text of the README and this report. The datasets, thresholds and conclusions "
           "were chosen and checked by me, and I can explain every part of the code.")
    doc.add_heading("Appendix B. Reproducing the results", 1)
    p(doc, "The repository README lists the setup in six steps. After the data are downloaded, the complete analysis runs with "
           "`docker compose run --rm pipeline`. The figures and this report are rebuilt with "
           "`python report/make_figures.py` and `python report/build_report.py`.")


def main():
    doc = setup()
    title(doc)
    framing(doc)
    data_section(doc)
    approach(doc)
    methods(doc)
    results(doc)
    limitations(doc)
    conclusion(doc)
    appendix(doc)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
