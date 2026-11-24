// JSONL {id, code} on stdin → JSONL {id, ok, error?, events?} on stdout.
import './quiet.mjs';
import { createInterface } from 'node:readline';
import { events } from './dialect.mjs';

for await (const line of createInterface({ input: process.stdin })) {
  if (!line.trim()) continue;
  const { id, code } = JSON.parse(line);
  try {
    process.stdout.write(JSON.stringify({ id, ok: true, events: events(code) }) + '\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({ id, ok: false, error: String(e.message).slice(0, 200) }) + '\n');
  }
}
