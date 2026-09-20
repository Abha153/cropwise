#!/usr/bin/env python3
"""CropWise i18n helper: status / dump / merge / validate.
Files use CRLF + 2-space indent + raw UTF-8 (ensure_ascii=False); we preserve that."""
import json, re, sys, os, collections, unicodedata
D = '/home/claude/work/frontend/src/i18n/translations'
MINE = ['te','gu','kn','as','bho','mai','ml','or','pa','ur']
SCRIPT = {'te':'TELUGU','gu':'GUJARATI','kn':'KANNADA','as':'BENGALI','bho':'DEVANAGARI','mai':'DEVANAGARI',
          'ml':'MALAYALAM','or':'ORIYA','pa':'GURMUKHI','ur':'ARABIC'}

def load_raw(code):
    dups = []
    def hook(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen: dups.append(k)
            seen.add(k)
        return dict(pairs)
    with open(f'{D}/{code}.json', encoding='utf-8') as f:
        txt = f.read()
    return json.loads(txt, object_pairs_hook=hook), dups, txt

def save(code, data):
    raw = open(f'{D}/{code}.json', encoding='utf-8', newline='').read()
    crlf = '\r\n' in raw; trail = raw.endswith('\n')
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    if crlf: txt = txt.replace('\n', '\r\n')
    if trail: txt += '\r\n' if crlf else '\n'
    with open(f'{D}/{code}.json', 'w', encoding='utf-8', newline='') as f:
        f.write(txt)
def load(code): return load_raw(code)[0]

TOK = re.compile(r'\{\{\s*[\w.]+\s*\}\}|\{[\w.]+\}|</?[a-zA-Z][^>]*>|%[sd]|\*\*|`|\\n|\n')
def tokens(s): return collections.Counter(re.sub(r'\s+', '', t) if t.startswith('{') else t for t in TOK.findall(s))

def check_value(en_v, v):
    errs = []
    if not isinstance(v, str): return ['not-a-string']
    if v.strip() == '': errs.append('empty')
    if v.strip() in ('TODO', 'Translation needed', 'undefined', 'null', 'None'): errs.append('filler')
    if tokens(en_v) != tokens(v): errs.append(f'placeholder-mismatch en={dict(tokens(en_v))} loc={dict(tokens(v))}')
    if '\ufffd' in v: errs.append('invalid-unicode(U+FFFD)')
    if any(unicodedata.category(c) == 'Cs' for c in v): errs.append('surrogate')
    return errs

def cmd_status():
    en = load('en'); print('Locale | Master Keys | Locale Keys | Missing | Extra | Status')
    for l in MINE:
        d = load(l); miss = [k for k in en if k not in d]; ex = [k for k in d if k not in en]
        print(f'{l} | {len(en)} | {len(d)} | {len(miss)} | {len(ex)} | {"PASS" if not miss and not ex else "INCOMPLETE"}')

def cmd_dump(code, ns_prefixes):
    """print global-index<TAB>english for missing keys in the given namespaces"""
    en = load('en'); d = load(code); keys = list(en)
    for i, k in enumerate(keys):
        if k in d: continue
        if ns_prefixes and not any(k == p or k.startswith(p + '.') for p in ns_prefixes): continue
        print(f'{i}\t{en[k]}')

def cmd_merge(code, batchfile, drop_extras=False):
    en = load('en'); keys = list(en); d = load(code)
    added = 0; bad = []
    for line in open(batchfile, encoding='utf-8'):
        line = line.rstrip('\n').rstrip('\r')
        if not line.strip(): continue
        m = re.match(r'^(\d+)[\t|]\s?(.*)$', line)
        if not m: bad.append((line[:40], 'bad-line')); continue
        i, v = m.group(1), m.group(2)
        k = keys[int(i)]
        v = v.replace('\\n', '\n') if '\n' in en[k] else v
        e = check_value(en[k], v)
        if e: bad.append((k, e)); continue
        if k in d and d[k] != en[k] and d[k].strip(): continue  # never overwrite an existing real translation
        d[k] = v; added += 1
    out = {k: d[k] for k in keys if k in d}
    extras = [k for k in d if k not in en]
    if not drop_extras:
        for k in extras: out[k] = d[k]
    save(code, out)
    print(f'{code}: merged {added}, rejected {len(bad)}, extras {"dropped" if drop_extras else "kept"} ({len(extras)})')
    for b in bad[:20]: print('  REJECT', b)

if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'status': cmd_status()
    elif a[0] == 'dump': cmd_dump(a[1], a[2:])
    elif a[0] == 'merge': cmd_merge(a[1], a[2], '--drop-extras' in a)
