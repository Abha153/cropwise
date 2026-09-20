"""
Generate missing translation patches for all 11 remaining locales.
Run from the workspace root: python i18n_audit/gen_translations.py
"""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

EN = json.load(open('frontend/src/i18n/translations/en.json', encoding='utf-8'))

def load(code):
    return json.load(open(f'frontend/src/i18n/translations/{code}.json', encoding='utf-8'))

def save(code, data):
    with open(f'frontend/src/i18n/translations/{code}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def apply_patch(code, patch):
    loc = load(code)
    before = len(loc)
    loc.update(patch)
    missing = sorted(set(EN.keys()) - set(loc.keys()))
    save(code, loc)
    print(f'{code}: {before} -> {len(loc)} keys, {len(missing)} still missing')
    if missing:
        print(f'  Still missing: {missing[:5]}')

# ── Tamil patch ──────────────────────────────────────────────────────────────
TA = {}
exec(open('i18n_audit/patch_ta.py', encoding='utf-8').read())
apply_patch('ta', TA)

# ── Telugu patch ─────────────────────────────────────────────────────────────
TE = {}
exec(open('i18n_audit/patch_te.py', encoding='utf-8').read())
apply_patch('te', TE)

# ── Gujarati patch ────────────────────────────────────────────────────────────
GU = {}
exec(open('i18n_audit/patch_gu.py', encoding='utf-8').read())
apply_patch('gu', GU)

# ── Kannada patch ─────────────────────────────────────────────────────────────
KN = {}
exec(open('i18n_audit/patch_kn.py', encoding='utf-8').read())
apply_patch('kn', KN)

# ── Malayalam patch ───────────────────────────────────────────────────────────
ML = {}
exec(open('i18n_audit/patch_ml.py', encoding='utf-8').read())
apply_patch('ml', ML)

# ── Punjabi patch ─────────────────────────────────────────────────────────────
PA = {}
exec(open('i18n_audit/patch_pa.py', encoding='utf-8').read())
apply_patch('pa', PA)
