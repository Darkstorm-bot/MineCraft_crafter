import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createBot } from 'mineflayer';
import pino from 'pino';
import { MineflayerNavigationAdapter } from '../dist/navigation.js';
import { MineflayerPlacementAdapter } from '../dist/placement.js';
import { MineflayerInventoryAdapter } from '../dist/inventory.js';
import { MineflayerWorldStateAdapter } from '../dist/world_state.js';
import { executeBuildTask, sanitizeBuildTask } from '../dist/executor.js';

const logger = pino({ name: 'execute-repaired-build' });

function sleep(ms) { return new Promise((res) => setTimeout(res, ms)); }

function sanitizeCommandForMinecraft(raw, preferPrefix = '//') {
  try {
    if (!raw && raw !== 0) return '';
    let s = String(raw);
    s = s.replace(/```[\s\S]*?```/g, '$1');
    s = s.replace(/`+/g, '');
    s = s.replace(/\s+/g, ' ').trim();
    s = s.replace(/^['"]+|['"]+$/g, '');
    const idxDouble = s.indexOf('//');
    if (idxDouble >= 0) {
      s = s.slice(idxDouble).split(/\r?\n/)[0].trim();
      return s;
    }
    const idxSlash = s.indexOf('/');
    if (idxSlash === 0) {
      s = s.split(/\r?\n/)[0].trim();
      return s;
    }
    if (/\b(schematic|paste|schem)\b/i.test(s)) {
      s = `${preferPrefix}${s.replace(/^\s+/, '')}`.trim();
      return s;
    }
    s = s.split(/\r?\n/)[0].trim();
    if (!s.startsWith('/') && !s.startsWith('//')) s = `${preferPrefix}${s}`;
    return s;
  } catch (e) {
    return '';
  }
}

async function run() {
  const botHost = process.env.MC_HOST || 'localhost';
  const botPort = process.env.MC_PORT ? Number(process.env.MC_PORT) : 25565;
  const botUser = process.env.MC_USER || 'autobot-runner';

  const repairedPath = fileURLToPath(new URL('../test_llm_repaired.json', import.meta.url));
  if (!fs.existsSync(repairedPath)) {
    console.error('Repaired BuildTask not found at', repairedPath);
    process.exit(2);
  }

  const raw = fs.readFileSync(repairedPath, 'utf8');
  const task = JSON.parse(raw);

  const bot = createBot({ host: botHost, port: botPort, username: botUser });

  bot.once('spawn', async () => {
    try {
      logger.info('Bot spawned, initializing adapters');
      const nav = new MineflayerNavigationAdapter(bot, logger);
      const place = new MineflayerPlacementAdapter(bot, logger);
      const inv = new MineflayerInventoryAdapter(bot, logger);
      const world = new MineflayerWorldStateAdapter(bot, logger);

      // wait a moment for world to be ready then sanitize and hand off to shared executor
      await sleep(2000);
      let execTask = task;
      try {
        execTask = sanitizeBuildTask(task, logger);
      } catch (sanErr) {
        logger.error({ err: sanErr }, 'Sanitization failed');
        try { bot.quit(); } catch (e) {}
        process.exit(1);
      }

      await executeBuildTask(bot, execTask, { nav, place, inv, world, logger });
      logger.info('Build task execution finished, sending confirmation chat');
      bot.chat('Build executed by script');
      await sleep(2000);
      try { bot.quit(); } catch (e) {}
      process.exit(0);
    } catch (e) {
      logger.error({ err: e }, 'Execution failed');
      try { bot.quit(); } catch (err) {}
      process.exit(1);
    }
  });

  bot.once('error', (err) => {
    logger.error({ err }, 'Bot error');
  });
}

run();
