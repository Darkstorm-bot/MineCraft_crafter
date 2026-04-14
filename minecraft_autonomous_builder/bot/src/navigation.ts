export interface NavigationAdapter {
  goto(x: number, y: number, z: number): Promise<void>;
}

export class MockNavigationAdapter implements NavigationAdapter {
  async goto(_x: number, _y: number, _z: number): Promise<void> {
    return;
  }
}
