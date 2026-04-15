import { Bot } from 'mineflayer';

export interface InventoryAdapter {
  count(item: string): Promise<number>;
  hasItems(required: Record<string, number>): Promise<{ ok: boolean; missing: Record<string, number> }>;
}

export class MineflayerInventoryAdapter implements InventoryAdapter {
  private bot: Bot;
  private logger: { info: (msg: string, ...args: any[]) => void; warn: (msg: string, ...args: any[]) => void; error: (msg: string, ...args: any[]) => void };

  constructor(bot: Bot, logger: any) {
    this.bot = bot;
    this.logger = logger;
  }

  async count(itemName: string): Promise<number> {
    const items = this.bot.inventory.items();
    const matching = items.filter(i => i.name === itemName || i.displayName?.includes(itemName));
    const total = matching.reduce((sum, i) => sum + i.count, 0);
    this.logger.info(`Inventory count for ${itemName}: ${total}`);
    return total;
  }

  async hasItems(required: Record<string, number>): Promise<{ ok: boolean; missing: Record<string, number> }> {
    const missing: Record<string, number> = {};

    for (const [item, needed] of Object.entries(required)) {
      const available = await this.count(item);
      if (available < needed) {
        missing[item] = needed - available;
      }
    }

    const ok = Object.keys(missing).length === 0;
    if (!ok) {
      this.logger.warn(`Missing items: ${JSON.stringify(missing)}`);
    }

    return { ok, missing };
  }

  async getInventorySnapshot(): Promise<Record<string, number>> {
    const items = this.bot.inventory.items();
    const snapshot: Record<string, number> = {};
    for (const item of items) {
      const name = item.name;
      snapshot[name] = (snapshot[name] || 0) + item.count;
    }
    return snapshot;
  }
}
