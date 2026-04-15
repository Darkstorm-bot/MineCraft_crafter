import fs from 'fs';
import path from 'path';
import { BuildTaskSchema } from '../dist/protocol.js';

const inPath = new URL('../test_llm_repaired.json', import.meta.url);
try {
  const raw = fs.readFileSync(inPath, 'utf8');
  const parsed = JSON.parse(raw);
  try {
    const task = BuildTaskSchema.parse(parsed);
    console.log('Validation successful. BuildTask:');
    console.log(JSON.stringify(task, null, 2));
    process.exit(0);
  } catch (e) {
    console.error('Zod validation failed:');
    console.error(e);
    process.exit(2);
  }
} catch (err) {
  console.error('Failed to read or parse repaired JSON:', err);
  process.exit(1);
}
