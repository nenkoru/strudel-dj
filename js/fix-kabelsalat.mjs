// @kabelsalat/* publish a CJS "main" that lacks the ESM exports @strudel/core imports;
// Node ignores "module", so point "main" at the ESM build.
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';

const dir = new URL('./node_modules/@kabelsalat/', import.meta.url);
if (existsSync(dir)) for (const name of readdirSync(dir)) {
  const file = new URL(`${name}/package.json`, dir);
  const pkg = JSON.parse(readFileSync(file, 'utf8'));
  if (pkg.module && pkg.main !== pkg.module) writeFileSync(file, JSON.stringify({ ...pkg, main: pkg.module }, null, 2));
}
