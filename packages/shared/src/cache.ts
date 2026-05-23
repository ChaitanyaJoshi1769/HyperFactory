export interface CacheOptions {
  ttl?: number;
}

export class Cache<K, V> {
  private cache: Map<K, { value: V; expiresAt?: number }> = new Map();

  constructor(private defaultTTL?: number) {}

  set(key: K, value: V, options?: CacheOptions): void {
    const ttl = options?.ttl ?? this.defaultTTL;
    const expiresAt = ttl ? Date.now() + ttl : undefined;
    this.cache.set(key, { value, expiresAt });
  }

  get(key: K): V | undefined {
    const item = this.cache.get(key);
    if (!item) return undefined;

    if (item.expiresAt && Date.now() > item.expiresAt) {
      this.cache.delete(key);
      return undefined;
    }

    return item.value;
  }

  has(key: K): boolean {
    return this.get(key) !== undefined;
  }

  delete(key: K): boolean {
    return this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  getOrSet(key: K, fn: () => V | Promise<V>, options?: CacheOptions): V | Promise<V> {
    const cached = this.get(key);
    if (cached !== undefined) return cached;

    const value = fn();
    if (value instanceof Promise) {
      return value.then((v) => {
        this.set(key, v, options);
        return v;
      });
    }

    this.set(key, value, options);
    return value;
  }

  size(): number {
    return this.cache.size;
  }

  keys(): K[] {
    return Array.from(this.cache.keys());
  }

  values(): V[] {
    return Array.from(this.cache.values()).map((item) => item.value);
  }
}

export const createCache = <K, V>(defaultTTL?: number): Cache<K, V> => {
  return new Cache<K, V>(defaultTTL);
};
