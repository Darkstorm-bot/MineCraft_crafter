export interface PlacementAdapter {
  paste(command: string): Promise<void>;
}

export class MockPlacementAdapter implements PlacementAdapter {
  async paste(_command: string): Promise<void> {
    return;
  }
}
