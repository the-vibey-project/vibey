// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The settings model: pure, so every screen and store agrees on it. Declared by `interfaces/settings-interface.ts`. */
import { DEFAULT_THEME_MODE, THEME_MODES } from '@vibey/core';
import type { ThemeMode } from '@vibey/core';
import type {
  KryptonSettings,
  NotificationClass,
  SettingsChange,
  SettingsModelInterface,
} from './interfaces/settings-interface';

export class SettingsModel implements SettingsModelInterface {
  static readonly CLASSES: readonly NotificationClass[] = [
    'gate',
    'finished',
    'failed',
    'budget',
    'unlimited-reminder',
    'device-paired',
  ];

  /** What each class is, in the words the Settings screen shows. */
  static readonly LABELS: Readonly<Record<NotificationClass, string>> = {
    gate: 'A gate needs you',
    finished: 'A run or an ULTRA pass finished',
    failed: 'A run failed or parked',
    budget: 'A budget step was reached',
    'unlimited-reminder': 'Reminder: spending has no cap',
    'device-paired': 'A device was paired',
  };

  readonly defaults: KryptonSettings = {
    theme: DEFAULT_THEME_MODE,
    sounds: true,
    volume: 0.6,
    notifications: {
      gate: true,
      finished: true,
      failed: true,
      budget: true,
      'unlimited-reminder': true,
      'device-paired': true,
    },
  };

  apply(settings: KryptonSettings, change: SettingsChange): KryptonSettings {
    switch (change.type) {
      case 'theme':
        return { ...settings, theme: change.theme };
      case 'sounds':
        return { ...settings, sounds: change.on };
      case 'volume':
        return { ...settings, volume: SettingsModel.clamp(change.volume) };
      case 'notification':
        return { ...settings, notifications: { ...settings.notifications, [change.which]: change.on } };
      case 'reset':
        return this.defaults;
    }
  }

  load(text: string | null): KryptonSettings {
    let stored: unknown;
    try {
      stored = text === null ? {} : JSON.parse(text);
    } catch {
      stored = {};
    }
    const record = typeof stored === 'object' && stored !== null ? (stored as Record<string, unknown>) : {};
    const notifications = typeof record.notifications === 'object' && record.notifications !== null
      ? (record.notifications as Record<string, unknown>)
      : {};
    return {
      theme: (THEME_MODES as readonly unknown[]).includes(record.theme) ? (record.theme as ThemeMode) : this.defaults.theme,
      sounds: typeof record.sounds === 'boolean' ? record.sounds : this.defaults.sounds,
      volume: typeof record.volume === 'number' ? SettingsModel.clamp(record.volume) : this.defaults.volume,
      notifications: Object.fromEntries(
        SettingsModel.CLASSES.map((which) => [
          which,
          typeof notifications[which] === 'boolean' ? notifications[which] : this.defaults.notifications[which],
        ]),
      ) as Record<NotificationClass, boolean>,
    };
  }

  save(settings: KryptonSettings): string {
    return JSON.stringify(settings);
  }

  private static clamp(volume: number): number {
    return Number.isFinite(volume) ? Math.min(1, Math.max(0, volume)) : 0;
  }
}
