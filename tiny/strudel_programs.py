"""Whole Strudel programs for the base model's corpus: the answers of Strudel-Synth (Decomposer,
arXiv 2607.01849; 21k programs written by Claude Opus from musical and code-style seeds), read
straight from its archive, one program per document (separated by a \x1e line, as tiny/piece.py's).

    python3 tiny/strudel_programs.py data/raw/dl/strudel-synth/strudel_synth.tar.gz tiny/data/strudel-pieces.txt.gz
"""
import gzip
import sys
import tarfile


def main(archive, out):
    n = chars = 0
    with tarfile.open(archive, 'r|gz') as tf, gzip.open(out, 'wt', compresslevel=6) as fo:
        for m in tf:
            if m.isfile() and m.name.endswith('.js') and '/answers/' in '/' + m.name:
                code = tf.extractfile(m).read().decode('utf-8', 'replace').strip()
                if code and '\x1e' not in code:
                    fo.write(code + '\n\x1e\n'); n += 1; chars += len(code)
    print(n, 'programs,', chars // 1000000, 'M chars')


if __name__ == '__main__':
    main(*sys.argv[1:3])
