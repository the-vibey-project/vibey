// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The composition root the editor and the headless CLI share. */
import type { Catalogue } from './catalogue-interface';
import type { HttpClientInterface } from './http-client-interface';
import type { ProcessRunnerInterface } from './process-runner-interface';
import type { RunServices } from './run-interface';
import type { RawSettings, ResolvedSettings } from './settings-interface';
import type { ClockInterface, IdSourceInterface } from './support-interface';

export interface ServicesOptions {
  readonly raw: Partial<RawSettings>;
  readonly environ: Readonly<Record<string, string | undefined>>;
  readonly platform: string;
  /** Who changes budgets from here: a label for the journal. */
  readonly actor: string;
  /** Open folders, where lanes are looked for too. */
  readonly workspaceRoots: () => readonly string[];
  readonly processes?: ProcessRunnerInterface;
  readonly http?: HttpClientInterface;
  readonly clock?: ClockInterface;
  readonly ids?: IdSourceInterface;
  readonly isExecutable?: (candidate: string) => boolean;
  /** A paired hub and this device's key for it: then vibey is reached through the hub, not the local command line. */
  readonly hub?: { readonly url: string; readonly key: string };
}

export interface ServicesInterface {
  readonly settings: ResolvedSettings;
  catalogue(reload?: boolean): Promise<Catalogue>;
  runServices(): Promise<RunServices>;
  paidDeclared(): boolean;
  journalFor(directory: string, repository: string): string;
}
