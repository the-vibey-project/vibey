// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The app's state: settings and the hub connection. On iOS and Android both live in the
 * Keychain or Keystore (expo-secure-store). On the web nothing is stored: the token stays in
 * memory, never in localStorage (ADR-0068's web hardening), so a reload connects again.
 */
import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Platform } from 'react-native';
import { HubClient, SettingsModel } from '../core';
import type { HubConnection, KryptonSettings, SettingsChange } from '../core';

const MODEL = new SettingsModel();
const KEYS = { settings: 'krypton.settings', connection: 'krypton.connection' } as const;

/** Where the app keeps what it keeps. Injected so tests and the web keep nothing on disk. */
export interface KeyValueStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

export class SecureKeyValueStore implements KeyValueStore {
  get(key: string): Promise<string | null> {
    return SecureStore.getItemAsync(key);
  }
  set(key: string, value: string): Promise<void> {
    return SecureStore.setItemAsync(key, value);
  }
  remove(key: string): Promise<void> {
    return SecureStore.deleteItemAsync(key);
  }
}

export class MemoryStore implements KeyValueStore {
  private readonly values = new Map<string, string>();
  async get(key: string): Promise<string | null> {
    return this.values.get(key) ?? null;
  }
  async set(key: string, value: string): Promise<void> {
    this.values.set(key, value);
  }
  async remove(key: string): Promise<void> {
    this.values.delete(key);
  }
}

export function defaultStore(): KeyValueStore {
  return Platform.OS === 'web' ? new MemoryStore() : new SecureKeyValueStore();
}

interface AppState {
  readonly ready: boolean;
  readonly settings: KryptonSettings;
  readonly connection: HubConnection | null;
  readonly client: HubClient | null;
  change(change: SettingsChange): void;
  connect(connection: HubConnection): Promise<void>;
  forget(): Promise<void>;
}

const Context = createContext<AppState | null>(null);

export function AppStateProvider(props: {
  readonly children: ReactNode;
  readonly store?: KeyValueStore;
  readonly fetchLike?: typeof fetch;
  readonly initial?: { readonly connection?: HubConnection; readonly settings?: KryptonSettings };
}) {
  const store = useMemo(() => props.store ?? defaultStore(), [props.store]);
  const [ready, setReady] = useState(props.initial !== undefined);
  const [settings, setSettings] = useState<KryptonSettings>(props.initial?.settings ?? MODEL.defaults);
  const [connection, setConnection] = useState<HubConnection | null>(props.initial?.connection ?? null);

  useEffect(() => {
    if (props.initial !== undefined) return;
    void (async () => {
      setSettings(MODEL.load(await store.get(KEYS.settings)));
      const saved = await store.get(KEYS.connection);
      if (saved !== null) {
        try {
          setConnection(JSON.parse(saved) as HubConnection);
        } catch {
          await store.remove(KEYS.connection);
        }
      }
      setReady(true);
    })();
  }, [store, props.initial]);

  const change = useCallback(
    (next: SettingsChange) => {
      setSettings((current) => {
        const updated = MODEL.apply(current, next);
        void store.set(KEYS.settings, MODEL.save(updated));
        return updated;
      });
    },
    [store],
  );

  const fetchLike = useMemo(() => props.fetchLike ?? globalThis.fetch.bind(globalThis), [props.fetchLike]);
  const connect = useCallback(
    async (next: HubConnection) => {
      // Proven before it is kept: a connection the hub refuses is never stored.
      await new HubClient(next, (url, init) => fetchLike(url, init)).projects();
      await store.set(KEYS.connection, JSON.stringify(next));
      setConnection(next);
    },
    [store, fetchLike],
  );

  const forget = useCallback(async () => {
    await store.remove(KEYS.connection);
    setConnection(null);
  }, [store]);

  const client = useMemo(
    () => (connection === null ? null : new HubClient(connection, (url, init) => fetchLike(url, init))),
    [connection, fetchLike],
  );

  const value = useMemo(
    () => ({ ready, settings, connection, client, change, connect, forget }),
    [ready, settings, connection, client, change, connect, forget],
  );
  return <Context.Provider value={value}>{props.children}</Context.Provider>;
}

export function useApp(): AppState {
  const state = useContext(Context);
  if (state === null) throw new Error('useApp outside AppStateProvider');
  return state;
}
