// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** `@vibey` in the chat view, where the editor has one: the same commands, and tasks streamed as text. */
import type * as vscode from 'vscode';

export interface VibeyChatInterface {
  /** Register the participant; nothing when this editor has no chat API. */
  register(): vscode.Disposable | undefined;
}
