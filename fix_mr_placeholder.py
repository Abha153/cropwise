import json, sys, collections, re

sys.stdout.reconfigure(encoding='utf-8')

path = 'frontend/src/i18n/translations/mr.json'

with open(path, encoding='utf-8') as f:
    mr = json.load(f, object_pairs_hook=collections.OrderedDict)

old = mr.get('advisor.forecastConfidence', '')
print('BEFORE:', repr(old))

# Fix: {{pct}} -> {{percent}}, keep Marathi text, add · {{source}} at end
# Pattern: "{{pct}}% अंदाज विश्वास" -> "{{percent}}% अंदाज विश्वास · {{source}}"
fixed = old.replace('{{pct}}', '{{percent}}')
if '{{source}}' not in fixed:
    fixed = fixed.rstrip() + ' · {{source}}'
mr['advisor.forecastConfidence'] = fixed
print('AFTER: ', repr(fixed))

with open(path, 'w', encoding='utf-8') as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)
    f.write('\n')

# Verify
TOK = re.compile(r'\{\{\s*[\w.]+\s*\}\}')
en_ph = sorted(TOK.findall('{{percent}}% forecast confidence · {{source}}'))
mr_ph = sorted(TOK.findall(fixed))
print('EN placeholders:', en_ph)
print('MR placeholders:', mr_ph)
print('MATCH:', en_ph == mr_ph)
