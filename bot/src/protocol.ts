import { z } from 'zod';

export const BatchEventSchema = z.object({
  batch_index: z.number().int().nonnegative(),
  blocks_placed: z.number().int().nonnegative(),
  status: z.enum(['ok', 'retry', 'failed'])
});

export type BatchEvent = z.infer<typeof BatchEventSchema>;


const PasteStep = z.object({
  action: z.literal('paste'),
  command: z.string().min(1)
});

const PlaceStep = z.object({
  action: z.literal('place'),
  command: z.string().min(1)
});

const WaitStep = z.object({
  action: z.literal('wait'),
  // duration in milliseconds
  duration_ms: z.number().int().nonnegative()
});

const Coords = z.object({ x: z.number(), y: z.number(), z: z.number() });

const RelativeTarget = z.object({
  relative: z.string().min(1),
  distance: z.number().int().nonnegative().optional()
});

const MoveStep = z.object({
  action: z.literal('move'),
  target: z.union([Coords, RelativeTarget])
});

const ChatStep = z.object({
  action: z.literal('chat'),
  message: z.string().min(1)
});

const CommandStep = z.object({
  action: z.literal('command'),
  // full server command (include leading / if needed)
  command: z.string().min(1)
});

export const BuildStepSchema = z.discriminatedUnion('action', [
  PasteStep,
  PlaceStep,
  WaitStep,
  MoveStep,
  ChatStep,
  CommandStep
]);

export const BuildTaskSchema = z.object({
  intent: z.string().min(1),
  schematic: z.string().optional(),
  target: z.union([Coords, RelativeTarget]).optional(),
  steps: z.array(BuildStepSchema).min(1)
});

export type BuildTask = z.infer<typeof BuildTaskSchema>;
