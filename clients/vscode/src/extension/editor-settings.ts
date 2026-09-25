// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The `vibey.*` settings as the core reads them. Every key the core knows is a declared
 * setting in package.json (sub-doctrine 12.c), and one unit test holds the two equal, so this
 * reads each by its own name and passes it on unchanged. Declared by
 * `interfaces/editor-settings-interface.ts`.
 */
import * as vscode from 'vscode';
import { Defaults } from '../core/settings';
import type { RawSettings } from '../core/interfaces/settings-interface';
import type { EditorSettingsInterface } from './interfaces/editor-settings-interface';

export class EditorSettings implements EditorSettingsInterface {
  static readonly SECTION = 'vibey';

  raw(): Partial<RawSettings> {
    const config = vscode.workspace.getConfiguration(EditorSettings.SECTION);
    const raw: Record<string, unknown> = {};
    for (const key of Object.keys(Defaults.SETTINGS)) {
      const value = config.get(EditorSettings.key(key));
      if (value !== undefined) {
        raw[key] = value;
      }
    }
    return raw as Partial<RawSettings>;
  }

  async set(key: string, value: unknown): Promise<void> {
    await vscode.workspace.getConfiguration(EditorSettings.SECTION).update(key, value, vscode.ConfigurationTarget.Global);
  }

  onChange(listener: () => void): vscode.Disposable {
    return vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration(EditorSettings.SECTION)) {
        listener();
      }
    });
  }

  /** The setting's key under `vibey.`: the core's names, except the allow-list's dotted one. */
  private static key(name: string): string {
    return name === 'environmentAllow' ? 'environment.allow' : name;
  }
}
