// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Interface for the Secondary Sidebar Chat Webview Provider (right column).
 */
import type * as vscode from 'vscode';
import type { TaskPanelInterface } from './panel-interface';

export interface ChatViewProviderInterface extends vscode.WebviewViewProvider, TaskPanelInterface {
  readonly isResolved: boolean;
  focus(): void;
}
