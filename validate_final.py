import json, sys, io, re, unicodedata, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)

en = load_json('frontend/src/i18n/translations/en.json')
en_keys = list(en.keys())
en_set = set(en_keys)

TOK = re.compile(r'\{\{\s*[\w.]+\s*\}\}|\{[\w.]+\}|</?[a-zA-Z][^>]*>|%[sd]|\*\*|`|\\n|\n')
def tokens(s):
    return collections.Counter(re.sub(r'\s+','',t) if t.startswith('{') else t for t in TOK.findall(s))

locales = ['hi','mr','bn','ta','te','gu','kn','as','bho','mai','ml','or','pa','ur']

print(f"{'Locale':<6} | {'en keys':<8} | {'loc keys':<8} | {'missing':<7} | {'extra':<5} | {'empty':<5} | {'placeholder_err':<14} | Status")
print("-"*80)

all_pass = True
for loc in locales:
    d = load_json(f'frontend/src/i18n/translations/{loc}.json')
    loc_keys = set(d.keys())

    missing = [k for k in en_set if k not in loc_keys]
    extra   = [k for k in loc_keys if k not in en_set]
    empty   = [k for k in en_set if k in d and not str(d[k]).strip()]
    ph_err  = []
    for k in en_set:
        if k in d and d[k] and str(d[k]).strip():
            if tokens(en[k]) != tokens(str(d[k])):
                ph_err.append(k)

    status = "PASS" if not missing and not empty and not ph_err else "INCOMPLETE"
    if status != "PASS":
        all_pass = False
    print(f"{loc:<6} | {len(en_set):<8} | {len(d):<8} | {len(missing):<7} | {len(extra):<5} | {len(empty):<5} | {len(ph_err):<14} | {status}")

    if missing:
        # Show first 5 missing
        for k in missing[:5]:
            print(f"         MISSING: {k}")
    if ph_err:
        for k in ph_err[:3]:
            print(f"         PH_ERR: {k}  en={dict(tokens(en[k]))}  loc={dict(tokens(str(d[k])))}")

print()
if all_pass:
    print("ALL LOCALES: PASS")
else:
    print("Some locales still have gaps.")
