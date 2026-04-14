export interface WorldStateAdapter {
  isChunkLoaded(_x: number, _z: number): Promise<boolean>;
}

export class MockWorldStateAdapter implements WorldStateAdapter {
  async isChunkLoaded(_x: number, _z: number): Promise<boolean> {
    return true;
  }
}
