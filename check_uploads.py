import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

root_files = ['as.json','bho.json','gu.json','kn.json','mai.json','ml.json','or.json','pa.json','te.json','ur.json']
scripts = ['i18n_tool.py','validate_all.py']

print("=== UPLOADED TRANSLATION FILES ===")
for f in root_files:
    if os.path.exists(f):
        d = json.load(open(f, encoding='utf-8'))
        items = list(d.items())[:3]
        first_val = items[0][1] if items else ''
        is_en = all(ord(c) < 256 for c in first_val)
        label = "ENGLISH" if is_en else "TRANSLATED"
        print(f"{f}: {len(d)} keys [{label}]: {first_val[:55]}")
    else:
        print(f"{f}: NOT FOUND")

print()
print("=== UPLOADED SCRIPTS ===")
for s in scripts:
    if os.path.exists(s):
        with open(s, encoding='utf-8') as fh:
            lines = fh.readlines()
        print(f"{s}: {len(lines)} lines")
        print(f"  First line: {lines[0].strip()}")
        print(f"  Second line: {lines[1].strip() if len(lines)>1 else ''}")
    else:
        print(f"{s}: NOT FOUND")

print()
print("=== merged.zip ===")
if os.path.exists('merged.zip'):
    import zipfile
    with zipfile.ZipFile('merged.zip') as z:
        names = z.namelist()
        print(f"merged.zip: {len(names)} entries")
        for n in names[:30]:
            print(f"  {n}")
        if len(names) > 30:
            print(f"  ... and {len(names)-30} more")
else:
    print("merged.zip: NOT FOUND")
