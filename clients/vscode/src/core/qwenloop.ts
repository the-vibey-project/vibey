// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The family's local agent runner (src/vibey_runners/qwen, the `qwenloop` package), which
 * ships as two programs since ADR-0061: `gptossloop`, the default, and `qwenloop`. The
 * extension drives either and writes no agent loop of its own (ADR-0017's dogfood rule).
 * Both take the same commands, as `qwenloop/cli/app.py` declares them:
 *   run PLAN --run-id --cwd --backend --base-url --model --effort --[no-]desktop-notifications
 *   prompt RUN_ID TEXT --cwd     (a follow-up; files a `prompt` control)
 *   stop RUN_ID --cwd            (files a `stop` control; the run winds down, exit 75)
 * `--effort` is accepted and not used by the runner. There is no `--context-window` flag:
 * the window comes only from the runner's config file (`context_window`, default 32768),
 * which its own `<PREFIX>_CONFIG` names (GPTOSSLOOP_CONFIG, QWENLOOP_CONFIG), so every run
 * gets a config file of its own.
 * Declared by `interfaces/qwenloop-interface.ts`.
 */
import type {
  Invocation,
  QwenloopCommandInterface,
  QwenloopRunArguments,
  QwenloopRunConfigInterface,
  RunConfigValues,
} from './interfaces/qwenloop-interface';
import { LocalRunners } from './local-runner';

export class QwenloopCommand implements QwenloopCommandInterface {
  /** The line a run prints when it finished the task, whichever name runs it. */
  static readonly DONE_MARKER = LocalRunners.PROTOCOL.doneMarker;
  /** `EXIT_CODE_WIND_DOWN`: the run stopped at a turn boundary because it was asked to. */
  static readonly EXIT_WOUND_DOWN = LocalRunners.PROTOCOL.exitWoundDown;

  constructor(private readonly executable: string) {}

  run(options: QwenloopRunArguments): Invocation {
    const args = [
      'run',
      options.planPath,
      '--run-id',
      options.runId,
      '--cwd',
      options.cwd,
      '--backend',
      'openai-compat',
      '--base-url',
      options.baseUrl,
      '--model',
      options.model,
      options.desktopNotifications ? '--desktop-notifications' : '--no-desktop-notifications',
    ];
    if (options.effort) {
      args.push('--effort', options.effort);
    }
    return { command: this.executable, args };
  }

  /**
   * The follow-up goes after `--`, so a message that starts with a dash is read as text and
   * never as an option.
   */
  prompt(runId: string, text: string, cwd: string): Invocation {
    return { command: this.executable, args: ['prompt', '--cwd', cwd, '--', runId, text] };
  }

  stop(runId: string, cwd: string): Invocation {
    return { command: this.executable, args: ['stop', '--cwd', cwd, '--', runId] };
  }

  version(): Invocation {
    return { command: this.executable, args: ['--version'] };
  }
}

export class QwenloopRunConfig implements QwenloopRunConfigInterface {
  /** The top-level keys a run sets; the user's own values for them are replaced, not stacked. */
  private static readonly OWNED = /^\s*(context_window|max_turns)\s*=/;
  private static readonly WINDOW = /^\s*context_window\s*=/;
  private static readonly TABLE = /^\s*\[/;

  compose(userConfig: string | undefined, values: RunConfigValues): string {
    const lines = ['# Written by the vibey VS Code extension for one run. Safe to delete.'];
    lines.push(`context_window = ${Math.floor(values.contextWindow)}`);
    if (values.maxTurns !== undefined) {
      lines.push(`max_turns = ${Math.floor(values.maxTurns)}`);
    }
    if (userConfig !== undefined) {
      lines.push('', '# The rest is the user\'s own runner config, unchanged.');
      const owned = values.maxTurns === undefined ? QwenloopRunConfig.WINDOW : QwenloopRunConfig.OWNED;
      let topLevel = true;
      for (const line of userConfig.split(/\r?\n/)) {
        topLevel = topLevel && !QwenloopRunConfig.TABLE.test(line);
        if (topLevel && owned.test(line)) {
          continue;
        }
        lines.push(line);
      }
    }
    return `${lines.join('\n').replace(/\n+$/, '')}\n`;
  }
}
