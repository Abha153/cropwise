const fs = require('fs');
const enRaw = fs.readFileSync('frontend/src/i18n/translations/en.json', 'utf8');
const hiRaw = fs.readFileSync('frontend/src/i18n/translations/hi.json', 'utf8');
const patchRaw = fs.readFileSync('i18n_audit/patch_hi.json', 'utf8');

function extractKeys(raw) {
  const keys = new Set();
  const lines = raw.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(/^\s+"([^"]+)"\s*:/);
    if (m) keys.add(m[1]);
  }
  return keys;
}

const enKeys = extractKeys(enRaw);
const hiKeys = extractKeys(hiRaw);
const patchKeys = extractKeys(patchRaw);

const missing = [];
enKeys.forEach(function(k) { if (!hiKeys.has(k)) missing.push(k); });
const uncovered = [];
missing.forEach(function(k) { if (!patchKeys.has(k)) uncovered.push(k); });

// Print all uncovered with en value
const enLines = enRaw.split('\n');
const enMap = {};
enLines.forEach(function(line) {
  const m = line.match(/^\s+"([^"]+)"\s*:\s*"(.*)"\s*,?\s*$/);
  if (m) enMap[m[1]] = m[2];
});

console.log('Total missing from HI: ' + missing.length);
console.log('Already in patch: ' + (missing.length - uncovered.length));
console.log('Still uncovered: ' + uncovered.length);
console.log('---');
uncovered.forEach(function(k) {
  console.log(k + '\t' + (enMap[k] || ''));
});
