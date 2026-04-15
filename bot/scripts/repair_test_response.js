import fs from 'fs';

function stripCodeFences(s) {
  if (!s) return s;
  // remove ```json ... ``` or ``` ... ```
  return s.replace(/```(?:json)?\s*([\s\S]*?)\s*```/, '$1').trim();
}

function tryParseCandidates(text) {
  if (!text) return null;
  try { return JSON.parse(text); } catch (_) {}
  // try to find first {...} block
  const m = text.match(/(\{[\s\S]*\})/);
  if (m) {
    try { return JSON.parse(m[0]); } catch (_) {}
  }
  return null;
}

const inPath = new URL('../test_llm_response.txt', import.meta.url);
const outPath = new URL('../test_llm_repaired.json', import.meta.url);

try {
  const raw = fs.readFileSync(inPath, 'utf8');
  let outer = null;
  try { outer = JSON.parse(raw); } catch (_) {
    // If file isn't a JSON object, treat as raw text
  }

  const resp = (outer && outer.response) ? outer.response : raw;
  const innerText = stripCodeFences(resp);
  let parsed = tryParseCandidates(innerText);
  if (!parsed) {
    console.error('Failed to parse inner JSON from response. Preview:\n', innerText.slice(0,2000));
    process.exit(2);
  }

  // Repair: schematic object -> string name
  if (parsed.schematic && typeof parsed.schematic === 'object' && !Array.isArray(parsed.schematic)) {
    const keys = Object.keys(parsed.schematic);
    if (keys.length === 1) {
      parsed.schematic = keys[0];
      console.log('Repaired schematic: converted object to string name', parsed.schematic);
    }
  }

  // Repair: typo actioniname -> action
  if (Array.isArray(parsed.steps)) {
    for (const step of parsed.steps) {
      if (step.actioniname && !step.action) {
        step.action = step.actioniname;
        delete step.actioniname;
        console.log('Repaired step: renamed actioniname -> action');
      }
    }
  }

  fs.writeFileSync(outPath, JSON.stringify(parsed, null, 2), 'utf8');
  console.log('Wrote repaired JSON to', outPath.pathname || outPath.href);
  console.log(JSON.stringify(parsed, null, 2).slice(0, 2000));
} catch (e) {
  console.error('Repair script failed:', e);
  process.exit(1);
}
