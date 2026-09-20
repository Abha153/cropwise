import sys, re, json, unicodedata
sys.path.insert(0,'/home/claude/tools')
import i18n_tool as T
en, endups, _ = T.load_raw('en')
print('Locale | Master Keys | Locale Keys | Missing | Extra | Status')
detail = {}
for l in T.MINE:
    try:
        d, dups, raw = T.load_raw(l)
    except Exception as e:
        print(l, 'MALFORMED JSON', e); continue
    miss = [k for k in en if k not in d]; extra = [k for k in d if k not in en]
    problems = []
    if dups: problems.append(('duplicate-keys', dups))
    for k, v in d.items():
        if k not in en: continue
        if v is None: problems.append((k, 'null')); continue
        if not isinstance(v, str): problems.append((k, f'non-string {type(v).__name__}')); continue
        for e in T.check_value(en[k], v): problems.append((k, e))
    # leftovers: identical to English (excluding allowlist-like short/technical) or mostly-Latin text
    ident = [k for k, v in d.items() if k in en and v == en[k]]
    latin = []
    for k, v in d.items():
        if k not in en or v == en[k]: continue
        stripped = re.sub(r'\{\{[^}]*\}\}|\{[^}]*\}|<[^>]*>', '', v)
        letters = [c for c in stripped if c.isalpha()]
        if letters and sum(1 for c in letters if 'LATIN' in unicodedata.name(c, '')) / len(letters) > .5:
            latin.append(k)
    detail[l] = dict(problems=problems, ident=ident, latin=latin, miss=miss, extra=extra)
    status = 'PASS' if not miss and not extra and not problems else 'INCOMPLETE' if not problems else 'FAIL'
    print(f'{l} | {len(en)} | {len(d)} | {len(miss)} | {len(extra)} | {status}')
print()
for l, x in detail.items():
    print(f'[{l}] value-problems={len(x["problems"])} identical-to-English={len(x["ident"])} mostly-Latin={len(x["latin"])}')
    for p in x['problems'][:5]: print('   ', p)
json.dump({l: {'miss': x['miss'], 'ident': x['ident'], 'latin': x['latin']} for l, x in detail.items()}, open('/home/claude/validation_detail.json', 'w'), ensure_ascii=False)
