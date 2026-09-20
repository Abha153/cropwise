import re, glob

files = glob.glob("src/**/*.jsx", recursive=True)
# crude heuristic: JSX text between > and < that has at least 2 alpha words, not starting with { (expression)
pattern = re.compile(r'>([^<>{}\n]{3,120})<')
skip_words = re.compile(r'^[\s\d.,:%₹$/\-–—()\[\]+*]*$')

hits = []
for fpath in files:
    with open(fpath, encoding="utf-8") as f:
        content = f.read()
    for lineno, line in enumerate(content.splitlines(), 1):
        for m in pattern.finditer(line):
            text = m.group(1).strip()
            if not text:
                continue
            if skip_words.match(text):
                continue
            # ignore pure JS template/expression artifacts
            if text.startswith('{') :
                continue
            # must contain a letter
            if not re.search(r'[A-Za-z]', text):
                continue
            # ignore things that are clearly variable-only, e.g. single identifiers with no space and no vowClass check skip
            words = text.split()
            if len(words) == 0:
                continue
            hits.append((fpath, lineno, text))

print(f"Total candidate hardcoded-text lines: {len(hits)}")
from collections import Counter
by_file = Counter(f for f,_,_ in hits)
for f,c in by_file.most_common(30):
    print(f"{c:4d}  {f}")
