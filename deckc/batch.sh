#!/bin/bash
# deckc/mine/batch.json for the rating page: 8 x N moments (N = 2nd argument, default 52) composed in
# parallel by deckc/batch.mjs. A small batch (N = 5: 40 moments, a few minutes) keeps a listen-and-fix
# loop short; grow it once a round sounds right.   [MODEL=http://localhost:8787] deckc/batch.sh [seed] [N]
set -euo pipefail
cd "$(dirname "$0")/.."
export NODE_PATH=js/node_modules
T=$(mktemp -d)
for i in 1 2 3 4 5 6 7 8; do node deckc/batch.mjs "${2:-52}" "${1:-0}$i" "$T/b$i.json" ${MODEL:-} 2>/dev/null & done
wait
node -e "
const fs = require('fs'); let all = [];
for (let i = 1; i <= 8; i++) all = all.concat(JSON.parse(fs.readFileSync('$T/b' + i + '.json', 'utf8')));
for (let i = all.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [all[i], all[j]] = [all[j], all[i]]; }  // workers' runs interleaved
fs.writeFileSync('deckc/mine/batch.json', JSON.stringify({ made: new Date().toISOString(), model: all[0].model, items: all }));
const c = {}; for (const x of all) for (const p of [x.a, x.b]) c[x.role + ':' + p.voice] = (c[x.role + ':' + p.voice] || 0) + 1;
console.log(all.length, 'items,', all[0].model); console.log(JSON.stringify(c));"
rm -r "$T"
