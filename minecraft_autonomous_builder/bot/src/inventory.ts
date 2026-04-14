export interface InventoryAdapter {
  count(item: string): Promise<number>;
}

export class MockInventoryAdapter implements InventoryAdapter {
  async count(_item: string): Promise<number> {
    return 999999;
  }
}
