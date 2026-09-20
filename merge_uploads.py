import json, zipfile, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

en = load_json('frontend/src/i18n/translations/en.json')
en_keys = set(en.keys())
print(f"Master en.json: {len(en)} keys")

# Sources per locale:
# 1. Live file: frontend/src/i18n/translations/{loc}.json
# 2. Root uploaded: {loc}.json  (10 locales: as,bho,gu,kn,mai,ml,or,pa,te,ur)
# 3. merged.zip/frontend/src/i18n/translations/{loc}.json (older state)

locales = ['ta','te','gu','kn','as','bho','mai','ml','or','pa','ur']

with zipfile.ZipFile('merged.zip') as z:
    for loc in locales:
        live = load_json(f'frontend/src/i18n/translations/{loc}.json')
        
        # Load from merged.zip (the snapshot)
        zip_path = f'frontend/src/i18n/translations/{loc}.json'
        try:
            zip_data = json.loads(z.read(zip_path).decode('utf-8'),
                                  object_pairs_hook=collections.OrderedDict)
        except:
            zip_data = {}
        
        # Load root uploaded file (if exists)
        import os
        root_data = {}
        if os.path.exists(f'{loc}.json'):
            root_data = load_json(f'{loc}.json')
        
        # Count valid keys in each source (key must be in en_keys and have non-empty value)
        def valid_count(d):
            return len([k for k in d if k in en_keys and d[k] and str(d[k]).strip()])
        
        live_count = valid_count(live)
        zip_count = valid_count(zip_data)
        root_count = valid_count(root_data)
        
        print(f"\n{loc}:")
        print(f"  live:  {live_count}/{len(en)} valid keys from en master")
        print(f"  zip:   {zip_count}/{len(en)}")
        print(f"  root:  {root_count}/{len(en)}")
        
        # Merge: start with live (most work done), then add from root, then zip
        merged = collections.OrderedDict(live)
        from_root = 0
        from_zip = 0
        
        for k in en_keys:
            if k not in merged or not str(merged.get(k,'')).strip():
                # Try root uploaded file first (newest)
                if k in root_data and root_data[k] and str(root_data[k]).strip():
                    merged[k] = root_data[k]
                    from_root += 1
                # Then try zip
                elif k in zip_data and zip_data[k] and str(zip_data[k]).strip():
                    merged[k] = zip_data[k]
                    from_zip += 1
        
        still_missing = len([k for k in en_keys if k not in merged or not str(merged.get(k,'')).strip()])
        save_json(f'frontend/src/i18n/translations/{loc}.json', merged)
        print(f"  merged: +{from_root} from root, +{from_zip} from zip -> {len([k for k in merged if k in en_keys])}/{len(en)} valid, {still_missing} still missing")

print("\nDone.")
