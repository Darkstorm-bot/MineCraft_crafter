import pino from 'pino';
import { MockInventoryAdapter } from './inventory';
import { MockNavigationAdapter } from './navigation';
import { MockPlacementAdapter } from './placement';
import { BatchEventSchema } from './protocol';
import { MockWorldStateAdapter } from './world_state';

const logger = pino({ name: 'minecraft-bot' });

async function main(): Promise<void> {
  const nav = new MockNavigationAdapter();
  const place = new MockPlacementAdapter();
  const world = new MockWorldStateAdapter();
  const inv = new MockInventoryAdapter();

  await nav.goto(0, 64, 0);
  const loaded = await world.isChunkLoaded(0, 0);
  const blocks = await inv.count('minecraft:stone');
  if (loaded && blocks > 0) {
    await place.paste('//paste -a 0,64,0');
  }

  const event = BatchEventSchema.parse({ batch_index: 0, blocks_placed: 10, status: 'ok' });
  logger.info({ event }, 'bot runtime ready');
}

main().catch((err) => {
  logger.error({ err }, 'bot runtime failed');
  process.exit(1);
});
