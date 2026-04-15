import fs from 'fs';

const ollamaUrl = process.env.OLLAMA_URL || 'http://localhost:11434';
const model = process.env.OLLAMA_MODEL || 'phi3:latest';

const prompt = `You are a JSON-only generator. Return exactly one JSON object and nothing else. The object must match this schema: {"intent": string, optional "schematic": string, optional "target": either {x:number,y:number,z:number} or {relative:string,distance:number}, "steps": array of steps}. Allowed step shapes: {"action":"paste", "command": string}, {"action":"place", "command": string}, {"action":"wait", "duration_ms": number}, {"action":"move", "target": {x,y,z} or {relative,distance}}, {"action":"chat", "message": string}, {"action":"command", "command": string}.

Create a BuildTask that constructs a small decorative Minecraft chicken directly in front of the player. Use a relative target describing "in front" with a distance of 2. Include a "schematic" field named "chicken_schematic" and steps that will: 1) paste the schematic (use a paste command like "//schematic load chicken_schematic" and "//paste"), 2) wait 2000 ms, 3) send a chat message "Chicken built". Be precise and minimal. Output only the JSON object, no surrounding text or explanation.`;

async function run() {
  try {
    const body = { model, prompt, max_tokens: 800, stream: false };
    const res = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    const raw = await res.text();
    console.log('HTTP', res.status, res.statusText);
    console.log('----- Response preview -----');
    console.log(raw.slice(0, 4000));

    const outPath = new URL('../test_llm_response.txt', import.meta.url);
    fs.writeFileSync(outPath, raw, 'utf8');
    console.log('Saved full response to', outPath.pathname || outPath.href);
  } catch (err) {
    console.error('Request failed:', err);
  }
}

run();
