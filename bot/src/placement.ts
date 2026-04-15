import { Bot } from 'mineflayer';
import { EventEmitter } from 'events';

export interface PlacementAdapter {
  paste(command: string): Promise<void>;
}

export class MineflayerPlacementAdapter extends EventEmitter implements PlacementAdapter {
  private bot: Bot;
  private logger: { info: (msg: string, ...args: any[]) => void; warn: (msg: string, ...args: any[]) => void; error: (msg: string, ...args: any[]) => void };
  private commandPrefix: string;
  private pendingCommands: Array<{ command: string; resolve: () => void; reject: (err: Error) => void }> = [];
  private processing = false;

  constructor(bot: Bot, logger: any, commandPrefix: string = '//') {
    super();
    this.bot = bot;
    this.logger = logger;
    this.commandPrefix = commandPrefix;

    // Listen for chat messages to detect command completion
    this.bot.on('chat', (username: string, message: string) => {
      if (message.includes('Complete') || message.includes('done') || message.includes('Pasted')) {
        this.processNext();
      }
    });
  }

  async paste(command: string): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      this.pendingCommands.push({ command, resolve, reject });
      if (!this.processing) {
        this.processNext();
      }
    });
  }

  private async processNext(): Promise<void> {
    if (this.pendingCommands.length === 0) {
      this.processing = false;
      return;
    }

    this.processing = true;
    const { command, resolve, reject } = this.pendingCommands.shift()!;

    try {
      this.logger.info(`Executing WorldEdit command: ${command}`);

      // Send command via chat
      this.bot.chat(command);

      // Wait for completion with timeout
      const timeout = setTimeout(() => {
        this.logger.warn(`Command timed out: ${command}`);
        resolve(); // Resolve anyway, let caller handle via retry
      }, 30000);

      // Wait a reasonable time for the paste to complete
      await new Promise<void>((res) => {
        const checkInterval = setInterval(() => {
          // Check if bot is still idle (no block placing animation)
          res();
          clearInterval(checkInterval);
        }, 5000);
        setTimeout(() => {
          clearInterval(checkInterval);
          res();
        }, 15000);
      });

      clearTimeout(timeout);
      this.logger.info(`Command completed: ${command}`);
      resolve();
    } catch (err: any) {
      this.logger.error(`Command failed: ${command} - ${err.message}`);
      reject(err);
    }
  }

  async pasteWithRetry(command: string, maxRetries: number = 3): Promise<void> {
    let lastError: Error | null = null;
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        await this.paste(command);
        return;
      } catch (err: any) {
        lastError = err;
        this.logger.warn(`Paste attempt ${attempt + 1}/${maxRetries} failed: ${err.message}`);
        await new Promise(resolve => setTimeout(resolve, 2000 * (attempt + 1)));
      }
    }
    throw new Error(`Paste failed after ${maxRetries} attempts: ${lastError?.message}`);
  }
}
