import sys


def main():
    paf, out = sys.argv[1], sys.argv[2]
    with open(paf) as f, open(out, "w") as o:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            query, qlen, qstart, qend = cols[0], int(cols[1]), int(cols[2]), int(cols[3])
            target, matches, block = cols[5], int(cols[9]), int(cols[10])
            if block == 0:
                continue
            identity = 100 * matches / block
            coverage = 100 * (qend - qstart) / qlen
            score = matches
            o.write(f"{query}\t{target}\t{identity:.2f}\t{block}\t{coverage:.1f}\t0\t{score}\n")


if __name__ == "__main__":
    main()
