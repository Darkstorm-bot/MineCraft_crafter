import { Vec3 } from 'vec3';
import { Bot } from 'mineflayer';
import { pathfinder, goals } from 'mineflayer-pathfinder';

export interface NavigationAdapter {
  goto(x: number, y: number, z: number): Promise<void>;
}

export class MineflayerNavigationAdapter implements NavigationAdapter {
  private bot: Bot;
  private logger: { info: (msg: string, ...args: any[]) => void; warn: (msg: string, ...args: any[]) => void; error: (msg: string, ...args: any[]) => void };

  constructor(bot: Bot, logger: any) {
    this.bot = bot;
    this.logger = logger;
    this.bot.loadPlugin(pathfinder);
  }

  async goto(x: number, y: number, z: number): Promise<void> {
    const goal = new goals.GoalNear(x, y, z, 2);
    this.logger.info(`Navigating to (${x}, ${y}, ${z})`);

    try {
      await this.bot.pathfinder.goto(goal);
      this.logger.info(`Arrived at (${x}, ${y}, ${z})`);
    } catch (err: any) {
      if (err.name === 'Invalid block') {
        this.logger.warn(`Pathfinding blocked, trying direct approach to (${x}, ${y}, ${z})`);
        // Try walking directly
        await this.bot.pathfinder.goto(new goals.GoalNear(x, y, z, 10));
      } else {
        this.logger.error(`Navigation failed: ${err.message}`);
        throw err;
      }
    }
  }

  async safeGoto(x: number, y: number, z: number, maxRetries: number = 3): Promise<void> {
    let lastError: Error | null = null;
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        await this.goto(x, y, z);
        return;
      } catch (err: any) {
        lastError = err;
        this.logger.warn(`Navigation attempt ${attempt + 1}/${maxRetries} failed: ${err.message}`);
        await new Promise(resolve => setTimeout(resolve, 2000 * (attempt + 1)));
      }
    }
    throw new Error(`Navigation failed after ${maxRetries} attempts: ${lastError?.message}`);
  }
}
