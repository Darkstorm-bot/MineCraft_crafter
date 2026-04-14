import { z } from 'zod';

export const BatchEventSchema = z.object({
  batch_index: z.number().int().nonnegative(),
  blocks_placed: z.number().int().nonnegative(),
  status: z.enum(['ok', 'retry', 'failed'])
});

export type BatchEvent = z.infer<typeof BatchEventSchema>;
