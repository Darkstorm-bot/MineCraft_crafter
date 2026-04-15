import { Bot } from 'mineflayer';

export interface WorldStateAdapter {
  isChunkLoaded(x: number, z: number): Promise<boolean>;
  getTPS(): Promise<number>;
  waitForStableTPS(threshold: number, timeoutMs: number): Promise<boolean>;
}

export class MineflayerWorldStateAdapter implements WorldStateAdapter {
  private bot: Bot;
  private logger: { info: (msg: string, ...args: any[]) => void; warn: (msg: string, ...args: any[]) => void; error: (msg: string, ...args: any[]) => void };
  private tpsHistory: number[] = [];

  constructor(bot: Bot, logger: any) {
    this.bot = bot;
    this.logger = logger;
  }

  async isChunkLoaded(chunkX: number, chunkZ: number): Promise<boolean> {
    // Convert block coordinates to chunk coordinates
    const cx = Math.floor(chunkX / 16);
    const cz = Math.floor(chunkZ / 16);

    // Check if the chunk is in the world
    try {
      const chunk = this.bot.world.getColumn(cx, cz);
      return chunk !== null && chunk !== undefined;
    } catch {
      // getColumn might not be available in all versions
      // Fallback: check if we can get blocks at that location
      try {
        const block = this.bot.blockAt(new (require('vec3').Vec3)(chunkX * 16, 64, chunkZ * 16));
        return block !== null;
      } catch {
        return false;
      }
    }
  }

  async getTPS(): Promise<number> {
    // Minecraft server TPS is typically 20.0
    // Estimate based on world tick updates
    // Since mineflayer doesn't directly expose TPS, we estimate it
    const now = Date.now();

    // Track tick timing
    if (!this.bot._lastTick) {
      this.bot._lastTick = now;
      return 20.0;
    }

    const delta = now - this.bot._lastTick;
    this.bot._lastTick = now;

    // Tick interval should be ~50ms for 20 TPS
    const estimatedTPS = Math.min(20.0, 1000 / delta);
    return estimatedTPS;
  }

  async waitForStableTPS(threshold: number = 18.0, timeoutMs: number = 30000): Promise<boolean> {
    this.logger.info(`Waiting for stable TPS >= ${threshold} (timeout: ${timeoutMs}ms)`);
    this.tpsHistory = [];

    const startTime = Date.now();
    const checkInterval = 1000; // Check every second

    return new Promise<boolean>((resolve) => {
      const checkTPS = async () => {
        const elapsed = Date.now() - startTime;
        if (elapsed > timeoutMs) {
          const avgTPS = this.tpsHistory.length > 0
            ? this.tpsHistory.reduce((a, b) => a + b, 0) / this.tpsHistory.length
            : 0;
          this.logger.warn(`TPS timeout: average ${avgTPS.toFixed(1)} TPS`);
          resolve(false);
          return;
        }

        const tps = await this.getTPS();
        this.tpsHistory.push(tps);

        // Keep last 5 samples
        if (this.tpsHistory.length > 5) {
          this.tpsHistory.shift();
        }

        if (this.tpsHistory.length >= 3) {
          const avgRecent = this.tpsHistory.slice(-3).reduce((a, b) => a + b, 0) / 3;
          if (avgRecent >= threshold) {
            this.logger.info(`TPS stable at ${avgRecent.toFixed(1)}`);
            resolve(true);
            return;
          }
        }

        setTimeout(checkTPS, checkInterval);
      };

      checkTPS();
    });
  }

  async waitForChunksAroundPosition(x: number, y: number, z: number, radius: number = 4): Promise<boolean> {
    this.logger.info(`Waiting for chunks around (${x}, ${y}, ${z}) radius ${radius}`);
    const startTime = Date.now();
    const timeoutMs = 30000;

    return new Promise<boolean>((resolve) => {
      const check = async () => {
        if (Date.now() - startTime > timeoutMs) {
          this.logger.warn('Chunk load timeout');
          resolve(false);
          return;
        }

        const chunkRadius = Math.ceil(radius / 16);
        const baseChunkX = Math.floor(x / 16);
        const baseChunkZ = Math.floor(z / 16);

        for (let dx = -chunkRadius; dx <= chunkRadius; dx++) {
          for (let dz = -chunkRadius; dz <= chunkRadius; dz++) {
            const loaded = await this.isChunkLoaded(baseChunkX + dx, baseChunkZ + dz);
            if (!loaded) {
              setTimeout(check, 1000);
              return;
            }
          }
        }

        this.logger.info('All chunks loaded');
        resolve(true);
      };

      check();
    });
  }
}
