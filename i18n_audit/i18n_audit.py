import json, re, glob, os

ROOT = "."
LOCALES = ["en","hi","mr","bn","ta","te","gu","kn","ml","pa","or","as","ur","bho","mai"]

dicts = {}
for code in LOCALES:
    path = f"src/i18n/translations/{code}.json"
    with open(path, encoding="utf-8") as f:
        dicts[code] = json.load(f)

en_keys = set(dicts["en"].keys())

report = {}
for code in LOCALES:
    keys = set(dicts[code].keys())
    missing = en_keys - keys
    extra = keys - en_keys
    # "fallback to english" = value identical to english value (not just key missing)
    identical_to_en = {k for k in keys & en_keys if dicts[code][k] == dicts["en"][k] and dicts["en"][k] != ""}
    report[code] = {
        "key_count": len(keys),
        "missing_count": len(missing),
        "missing_sample": sorted(list(missing))[:15],
        "extra_count": len(extra),
        "identical_to_english_count": len(identical_to_en),
    }

print("=== KEY COUNTS ===")
for code in LOCALES:
    r = report[code]
    print(f"{code}: keys={r['key_count']} missing={r['missing_count']} extra={r['extra_count']} identical_to_en_value={r['identical_to_english_count']}")

print()
print("=== MISSING KEY SAMPLES (first 15) ===")
for code in LOCALES:
    if report[code]["missing_count"]:
        print(f"-- {code} --")
        for k in report[code]["missing_sample"]:
            print("   ", k)

with open("/home/claude/work/i18n_report.json","w",encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
