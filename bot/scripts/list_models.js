const ollamaUrl = process.env.OLLAMA_URL || 'http://localhost:11434';

async function run() {
  try {
    const res = await fetch(`${ollamaUrl}/api/tags`);
    const txt = await res.text();
    console.log('HTTP', res.status, res.statusText);
    try {
      const j = JSON.parse(txt);
      console.log('Parsed /api/tags JSON:', JSON.stringify(j, null, 2));
      if (Array.isArray(j)) return;
      if (j && typeof j === 'object' && Array.isArray(j.tags)) console.log('tags:', j.tags);
    } catch (_) {
      console.log('Raw /api/tags output:', txt.slice(0, 2000));
    }
  } catch (e) {
    console.error('Failed to contact Ollama:', e);
    process.exit(2);
  }
}

run();
