
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('frontend/src/i18n/translations/en.json', encoding='utf-8') as f:
    en = json.load(f)

with open('frontend/src/i18n/translations/mr.json', encoding='utf-8') as f:
    mr = json.load(f)

print('mr advisor.forecastConfidence:', repr(mr.get('advisor.forecastConfidence')))
print('en advisor.forecastConfidence:', repr(en.get('advisor.forecastConfidence')))

with open('frontend/src/i18n/translations/as.json', encoding='utf-8') as f:
    a = json.load(f)
extras = [k for k in a if k not in en]
print('as extras:', extras)
