// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The one hub on this computer, from a UI (#1186). Every krypton UI offers start, stop and
 * status, and each of them runs `vibey hub status | start | stop`, so the editor, the desktop
 * app and a terminal agree on one rule: there is one hub per user, and closing a UI never
 * stops it. These calls always go to the local `vibey`, never through a paired hub or the
 * repository's GitHub workflows (`vibey --workflows`): the hub they act on is this
 * computer's. Declared by `interfaces/hub-engine-interface.ts`.
 */
import type { HubAction, HubEngineInterface, HubReport } from './interfaces/hub-engine-interface';
import type { Environment, ProcessRunnerInterface, RunOptions } from './interfaces/process-runner-interface';
import { VibeyCliError } from './vibey-cli';

export class HubEngine implements HubEngineInterface {
  /** `vibey hub status` exits with this when no hub runs: a fact, not a failure. */
  static readonly NOT_RUNNING = 3;

  constructor(
    private readonly runner: ProcessRunnerInterface,
    private readonly executable: string,
    private readonly environment: Environment,
    private readonly cwd?: string,
    private readonly timeoutMs = 60_000,
  ) {}

  async run(action: HubAction): Promise<HubReport> {
    const options: RunOptions = { env: this.environment, timeoutMs: this.timeoutMs, ...(this.cwd === undefined ? {} : { cwd: this.cwd }) };
    const result = await this.runner.run(this.executable, ['hub', action], options);
    const said = (result.stdout.trim() || result.stderr.trim()).trim();
    if (result.code === 0) {
      return { action, running: action !== 'stop', message: said };
    }
    if (action === 'status' && result.code === HubEngine.NOT_RUNNING) {
      return { action, running: false, message: said || 'The vibey hub is not running.' };
    }
    if (/No such command/i.test(`${result.stderr}\n${result.stdout}`)) {
      throw new VibeyCliError(
        `This vibey (${this.executable}) has no "vibey hub ${action}" command; it was added after the release that shipped "vibey hub pair". Point the vibey.cliPath setting at a newer vibey.`,
        'missing-command',
      );
    }
    throw new VibeyCliError(`vibey hub ${action} failed: ${said || result.error || `exit ${result.code}`}`, 'failed');
  }

  async ensure(): Promise<HubReport> {
    const status = await this.run('status');
    return status.running ? status : this.run('start');
  }
}
