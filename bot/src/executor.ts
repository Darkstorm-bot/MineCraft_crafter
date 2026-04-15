import type { Bot } from 'mineflayer';
import type { BuildTask } from './protocol.js';
import { MineflayerNavigationAdapter } from './navigation.js';
import { MineflayerPlacementAdapter } from './placement.js';
import { MineflayerInventoryAdapter } from './inventory.js';
import { MineflayerWorldStateAdapter } from './world_state.js';

function sleep(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}

function sanitizeCommandForMinecraft(raw: any, preferPrefix = '//') {
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

export async function executeBuildTask(bot: Bot, task: BuildTask, ctx: { nav: any; place: any; inv: any; world: any; logger: any; username?: string }) {
  const { nav, place, inv, world, logger, username } = ctx;

  for (const step of task.steps) {
    const action = String((step as any).action || '').toLowerCase();
    try {
      switch (action) {
        case 'paste':
        case 'place': {
          const rawCmd = (step as any).command || '';
          const cmd = sanitizeCommandForMinecraft(rawCmd, '//');
          if (!cmd) {
            logger?.warn({ rawCmd }, 'Skipping paste/place step: command empty or invalid');
            break;
          }
          if (typeof place.pasteWithRetry === 'function') {
            await place.pasteWithRetry(cmd);
          } else {
            await place.paste(cmd);
          }
          break;
        }
        case 'wait': {
          const ms = Number((step as any).duration_ms || 1000) || 1000;
          await sleep(ms);
          break;
        }
        case 'move': {
          const t = (step as any).target;
          if (!t) break;
          if (typeof t.x === 'number') {
            await nav.goto(t.x, t.y, t.z);
            break;
          }

          const rel = t.relative;
          const distance = Number(t.distance || 2) || 2;
          if (!rel) break;

          // determine source position and yaw: prefer the command sender when available
          let srcPos: any = null;
          let yaw = (bot as any).entity?.yaw ?? 0;
          try {
            if (username) {
              const player = (bot as any).players?.[username];
              if (player && player.entity && player.entity.position) {
                srcPos = player.entity.position;
                yaw = player.entity.yaw ?? yaw;
              }
            }
            if (!srcPos && (bot as any).entity && (bot as any).entity.position) {
              srcPos = (bot as any).entity.position;
            }
          } catch (_e) {
            srcPos = (bot as any).entity?.position;
          }

          if (!srcPos) break;

          const forwardX = -Math.sin(yaw) * distance;
          const forwardZ = Math.cos(yaw) * distance;
          const targetX = Math.round(srcPos.x + forwardX);
          const targetY = Math.round(srcPos.y);
          const targetZ = Math.round(srcPos.z + forwardZ);
          await nav.goto(targetX, targetY, targetZ);
          break;
        }
        case 'chat': {
          const msg = String((step as any).message || '').trim();
          if (!msg) {
            logger?.warn({ step }, 'Skipping chat step: empty message');
            break;
          }
          bot.chat(msg);
          break;
        }
        case 'command': {
          const rawCmd = (step as any).command || '';
          const cmd = sanitizeCommandForMinecraft(rawCmd, '/');
          if (!cmd) {
            logger?.warn({ rawCmd }, 'Skipping command step: empty or invalid');
            break;
          }
          bot.chat(cmd);
          break;
        }
        default:
          logger?.warn({ step }, 'Unknown build step action');
      }
    } catch (e) {
      logger?.error({ err: e, step }, 'Build step failed');
      throw e;
    }
  }
}

export default executeBuildTask;

export function sanitizeBuildTask(task: BuildTask, logger?: any): BuildTask {
  const MAX_COMMAND_LENGTH = 2000;
  const MAX_CHAT_LENGTH = 300;
  const MAX_WAIT_MS = 60000;
  const MAX_DISTANCE = 50;

  const prohibitedPatterns = [
    /\bop\b/i,
    /\bdeop\b/i,
    /\bban\b/i,
    /\bkick\b/i,
    /\bwhitelist\b/i,
    /\bstop\b/i,
    /\brestart\b/i,
    /\breload\b/i,
    /\bshutdown\b/i,
    /\bdelete\b/i,
    /\brm\b/i,
    /\bdel\b/i
  ];

  const allowedActions = new Set(['paste', 'place', 'wait', 'move', 'chat', 'command']);

  const out: any = { ...task, steps: [] };

  for (const step of task.steps || []) {
    try {
      if (!step || typeof step !== 'object') continue;
      const action = String((step as any).action || '').toLowerCase();
      if (!allowedActions.has(action)) {
        logger?.warn({ step }, 'sanitizeBuildTask: removing unsupported action');
        continue;
      }

      if (action === 'paste' || action === 'place' || action === 'command') {
        const prefer = action === 'command' ? '/' : '//';
        const raw = (step as any).command || '';
        const cmd = sanitizeCommandForMinecraft(raw, prefer);
        if (!cmd) {
          logger?.warn({ raw }, 'sanitizeBuildTask: removed empty command');
          continue;
        }

        // refuse commands that match prohibited patterns
        if (prohibitedPatterns.some((r) => r.test(cmd))) {
          logger?.warn({ cmd }, 'sanitizeBuildTask: command contains prohibited token, skipping');
          continue;
        }

        if (cmd.length > MAX_COMMAND_LENGTH) {
          logger?.warn({ len: cmd.length }, 'sanitizeBuildTask: command too long, skipping');
          continue;
        }

        // split multi-line commands into separate steps
        const parts = String(cmd).split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
        for (const p of parts) {
          out.steps.push({ action, command: p });
        }

        continue;
      }

      if (action === 'chat') {
        let msg = String((step as any).message || '').replace(/[\x00-\x1F\x7F]/g, '');
        msg = msg.replace(/\s+/g, ' ').trim();
        if (!msg) {
          logger?.warn({ step }, 'sanitizeBuildTask: empty chat message, skipping');
          continue;
        }
        if (msg.length > MAX_CHAT_LENGTH) msg = msg.slice(0, MAX_CHAT_LENGTH) + '...';
        out.steps.push({ action: 'chat', message: msg });
        continue;
      }

      if (action === 'wait') {
        let ms = Number((step as any).duration_ms || 1000) || 1000;
        ms = Math.max(0, Math.min(MAX_WAIT_MS, Math.floor(ms)));
        out.steps.push({ action: 'wait', duration_ms: ms });
        continue;
      }

      if (action === 'move') {
        const t = (step as any).target;
        if (!t) {
          logger?.warn({ step }, 'sanitizeBuildTask: move without target, skipping');
          continue;
        }
        if (typeof t.x === 'number') {
          const x = Number(t.x), y = Number(t.y), z = Number(t.z);
          if ([x, y, z].some((v) => Number.isNaN(v))) {
            logger?.warn({ target: t }, 'sanitizeBuildTask: move coords invalid, skipping');
            continue;
          }
          out.steps.push({ action: 'move', target: { x: Math.round(x), y: Math.round(y), z: Math.round(z) } });
          continue;
        }

        // relative
        const rel = String(t.relative || '').trim();
        if (!rel) {
          logger?.warn({ target: t }, 'sanitizeBuildTask: move relative missing, skipping');
          continue;
        }
        let distance = Number(t.distance || 2) || 2;
        distance = Math.max(0, Math.min(MAX_DISTANCE, Math.floor(distance)));
        out.steps.push({ action: 'move', target: { relative: rel, distance } });
        continue;
      }
    } catch (e) {
      logger?.warn({ err: e, step }, 'sanitizeBuildTask: error processing step, skipping');
      continue;
    }
  }

  if (!Array.isArray(out.steps) || out.steps.length === 0) {
    throw new Error('sanitizeBuildTask removed all steps; aborting');
  }

  // preserve intent/schematic/target from original where present
  const result: any = { intent: String(task.intent || '').slice(0, 256) };
  if ((task as any).schematic) result.schematic = (task as any).schematic;
  if ((task as any).target) result.target = (task as any).target;
  result.steps = out.steps;
  return result as BuildTask;
}
