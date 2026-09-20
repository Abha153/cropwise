"""
Master i18n fill+fix script for CropWise.
Steps:
  1. Load en.json (master, 1455 keys)
  2. Fix mr.json placeholder bug
  3. Fill all missing keys per locale
  4. Validate after each write
  5. Print final report
"""
import json, re, sys, collections, os
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'frontend/src/i18n/translations/'

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)

def save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

TOK = re.compile(r'\{\{\s*[\w.]+\s*\}\}')
def ph(s): return sorted(re.findall(TOK, str(s)))

def validate(en, d):
    missing = [k for k in en if k not in d]
    extra   = [k for k in d  if k not in en]
    ph_errs = [(k, ph(en[k]), ph(d[k])) for k in en if k in d and d[k] and ph(en[k]) != ph(str(d[k]))]
    empty   = [k for k in en if k in d and not str(d.get(k,'')).strip()]
    return missing, extra, ph_errs, empty

en = load(BASE + 'en.json')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Fix mr.json placeholder bug
# ─────────────────────────────────────────────────────────────────────────────
mr = load(BASE + 'mr.json')
before_mr_ph = ph(mr.get('advisor.forecastConfidence',''))
# Fix: replace {{pct}} with {{percent}} and append {{source}}
if '{{pct}}' in mr.get('advisor.forecastConfidence',''):
    old_val = mr['advisor.forecastConfidence']
    mr['advisor.forecastConfidence'] = old_val.replace('{{pct}}%', '{{percent}}%').rstrip() + ' · {{source}}'
    if '{{source}}' not in mr['advisor.forecastConfidence']:
        mr['advisor.forecastConfidence'] += ' · {{source}}'
save(BASE + 'mr.json', mr)
print(f"STEP 2: mr.json advisor.forecastConfidence fixed: {before_mr_ph} -> {ph(mr['advisor.forecastConfidence'])}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Translation tables for each locale
# Each dict maps en.json key -> translated string for that locale.
# Keys already in the locale file will NOT be overwritten.
# Placeholder {{names}} must exactly match en.json.
# ─────────────────────────────────────────────────────────────────────────────
