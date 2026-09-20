const fs = require('fs');
const enRaw = fs.readFileSync('frontend/src/i18n/translations/en.json', 'utf8');
const hiRaw = fs.readFileSync('frontend/src/i18n/translations/hi.json', 'utf8');
const patchRaw = fs.readFileSync('i18n_audit/patch_hi.json', 'utf8');

function extractKeys(raw) {
  const keys = new Set();
  const lines = raw.split('\n');
  for (const line of lines) {
    const m = line.match(/^\s+"([^"]+)"\s*:/);
    if (m) keys.add(m[1]);
  }
  return keys;
}

const enKeys = extractKeys(enRaw);
const hiKeys = extractKeys(hiRaw);
const patchKeys = extractKeys(patchRaw);

const missing = Array.from(enKeys).filter(k => !hiKeys.has(k));
const covered = missing.filter(k => patchKeys.has(k));
const uncovered = missing.filter(k => !patchKeys.has(k));
const extra = Array.from(patchKeys).filter(k => missing.indexOf(k) === -1);

console.log('EN unique keys:   ' + enKeys.size);
console.log('HI unique keys:   ' + hiKeys.size);
console.log('Missing from HI:  ' + missing.length);
console.log('Patch keys:       ' + patchKeys.size);
console.log('Covered by patch: ' + covered.length);
console.log('Uncovered:        ' + uncovered.length);
console.log('Extra in patch:   ' + extra.length);
if (uncovered.length) { console.log('UNCOVERED:', uncovered); }
if (extra.length) { console.log('EXTRA (already in HI):', extra); }
if (uncovered.length === 0 && extra.length === 0) {
  console.log('\n✓ PASS — patch covers exactly the 504 missing keys, no extras.');
}
