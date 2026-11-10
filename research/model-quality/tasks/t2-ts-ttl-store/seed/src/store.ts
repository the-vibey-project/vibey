export interface KeyValueStore {
  get(key: string): string | undefined;
  set(key: string, value: string): void;
  delete(key: string): boolean;
  keys(): string[];
}

export class MemoryStore implements KeyValueStore {
  private data = new Map<string, string>();

  get(key: string): string | undefined {
    return this.data.get(key);
  }

  set(key: string, value: string): void {
    this.data.set(key, value);
  }

  delete(key: string): boolean {
    return this.data.delete(key);
  }

  keys(): string[] {
    return [...this.data.keys()];
  }
}
