// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The `vibey.*` settings, read from and written to the editor's configuration. */
import type * as vscode from 'vscode';
import type { RawSettings } from '../../core/interfaces/settings-interface';

export interface EditorSettingsInterface {
  /** Every `vibey.*` setting the person has, as the core's raw settings. */
  raw(): Partial<RawSettings>;
  /** Write one setting (its key without `vibey.`) for this person, in every window. */
  set(key: string, value: unknown): Promise<void>;
  onChange(listener: () => void): vscode.Disposable;
}
