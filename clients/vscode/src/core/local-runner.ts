// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The family's local runner, under both names it ships as (ADR-0062). One package
 * (src/vibey_runners/qwen) installs two programs that differ only in who they are:
 *
 *   gptossloop  GPTOSSLOOP_* settings, `<user config dir>/gptossloop/config.toml`, asks for
 *               gpt-oss:20b; vibey switches it on unless VIBEY_FEATURE_GPTOSSLOOP=0.
 *   qwenloop    QWENLOOP_* settings, `<user config dir>/qwenloop/config.toml`, asks for
 *               qwen3:14b by its own config; on only when VIBEY_FEATURE_QWENLOOP=1.
 *
 * Everything else is the runner's one protocol, the same whichever name runs: the `.qwenloop`
 * state directory, the done marker, the verdict fence, the wind-down exit code, the command
 * verbs and the `--[no-]desktop-notifications` flag. This table is the only place the
 * extension knows either name; everything that binds a runner's settings reads it. Declared
 * by `interfaces/local-runner-interface.ts`.
 */
import type {
  LocalRunnersInterface,
  RunnerIdentity,
  RunnerProtocolInterface,
  RunnerVariable,
} from './interfaces/local-runner-interface';

export class LocalRunners implements LocalRunnersInterface {
  /** The runner's shared protocol (qwenloop cli/app.py and application/runner.py). */
  static readonly PROTOCOL: RunnerProtocolInterface = {
    stateDir: '.qwenloop',
    doneMarker: 'QWENLOOP_TASK_FULLY_COMPLETE',
    verdictFence: 'qwenloop-verdict',
    exitWoundDown: 75,
  };

  /** The sovereign default, on GPT-OSS (`GPTOSSLOOP` in the runner's domain/config.py). */
  static readonly GPTOSSLOOP: RunnerIdentity = {
    name: 'gptossloop',
    envPrefix: 'GPTOSSLOOP',
    defaultModel: 'gpt-oss:20b',
    onByDefault: true,
    pathSetting: 'gptossloopPath',
  };

  /** The same runner on a Qwen model, opt-in; its own config chooses the model. */
  static readonly QWENLOOP: RunnerIdentity = {
    name: 'qwenloop',
    envPrefix: 'QWENLOOP',
    defaultModel: null,
    onByDefault: false,
    pathSetting: 'qwenloopPath',
  };

  /** The family as it ships today: gptossloop first, as the default. */
  static readonly FAMILY = new LocalRunners([LocalRunners.GPTOSSLOOP, LocalRunners.QWENLOOP]);

  readonly default: RunnerIdentity;

  /** `runners` in order of preference: the first is the default. */
  constructor(
    readonly all: readonly [RunnerIdentity, ...RunnerIdentity[]],
    readonly protocol: RunnerProtocolInterface = LocalRunners.PROTOCOL,
  ) {
    this.default = all[0];
  }

  identify(engineId: string): RunnerIdentity | undefined {
    return this.all.find((runner) => runner.name === engineId);
  }

  variable(runner: RunnerIdentity, name: RunnerVariable): string {
    return `${runner.envPrefix}_${name}`;
  }

  passthrough(runner: RunnerIdentity): string {
    return `${runner.envPrefix}_*`;
  }
}
