// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A device's own settings: theme, sounds and which notifications it wants. Never a secret. */
import type { ThemeMode } from '@vibey/core';

/** The notification classes every Krypton client offers (Lane J's one event model). */
export type NotificationClass =
  | 'gate'
  | 'finished'
  | 'failed'
  | 'budget'
  | 'unlimited-reminder'
  | 'device-paired';

export interface KryptonSettings {
  readonly theme: ThemeMode;
  readonly sounds: boolean;
  /** 0 to 1. */
  readonly volume: number;
  readonly notifications: Readonly<Record<NotificationClass, boolean>>;
}

export type SettingsChange =
  | { readonly type: 'theme'; readonly theme: ThemeMode }
  | { readonly type: 'sounds'; readonly on: boolean }
  | { readonly type: 'volume'; readonly volume: number }
  | { readonly type: 'notification'; readonly which: NotificationClass; readonly on: boolean }
  | { readonly type: 'reset' };

export interface SettingsModelInterface {
  readonly defaults: KryptonSettings;
  apply(settings: KryptonSettings, change: SettingsChange): KryptonSettings;
  /** Stored text back into settings; anything unreadable falls back to the default, field by field. */
  load(text: string | null): KryptonSettings;
  save(settings: KryptonSettings): string;
}
