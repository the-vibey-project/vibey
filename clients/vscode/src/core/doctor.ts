// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * `Check my setup`, and `vibey-vscode doctor`: every piece, with the path it resolved and its
 * version, because on one machine the first `vibey` on PATH was an older release without the
 * new commands. Ollama's context window is judged by the model it really loaded (/api/ps),
 * never by a setting, and is "unknown" until a model is loaded. Declared by
 * `interfaces/doctor-interface.ts`.
 */
import type { Catalogue } from './interfaces/catalogue-interface';
import type { CheckStatus, DoctorCheck, DoctorInterface } from './interfaces/doctor-interface';
import type { ForbiddenEnvironmentInterface, SourceEnvironment } from './interfaces/environment-interface';
import type { OllamaAdviceInterface, OllamaProbeInterface, Platform } from './interfaces/ollama-interface';
import type { Environment, ProcessRunnerInterface } from './interfaces/process-runner-interface';
import type { ExecutableLocatorInterface, ResolvedSettings } from './interfaces/settings-interface';
import type { DurabilityGateInterface } from './interfaces/storage-interface';

export interface DoctorDependencies {
  readonly settings: ResolvedSettings;
  readonly platform: Platform;
  readonly gate: DurabilityGateInterface;
  readonly locator: ExecutableLocatorInterface;
  readonly processes: ProcessRunnerInterface;
  readonly environment: Environment;
  readonly probe: OllamaProbeInterface;
  readonly advice: OllamaAdviceInterface;
  readonly catalogue: () => Promise<Catalogue>;
  readonly environ: SourceEnvironment;
  readonly forbidden: ForbiddenEnvironmentInterface;
  readonly paidDeclared: () => boolean;
}

export class Doctor implements DoctorInterface {
  /** The vibey commands the views need, and the release that adds them. */
  static readonly VIBEY_COMMANDS = ['projects', 'gates', 'loops', 'budget'];

  constructor(private readonly deps: DoctorDependencies) {}

  async run(): Promise<readonly DoctorCheck[]> {
    const checks: DoctorCheck[] = [this.home()];
    checks.push(await this.program('git', this.deps.settings.raw.gitPath, 'fail', ['Install git: https://git-scm.com/downloads']));
    checks.push(
      await this.program('qwenloop', this.deps.settings.raw.qwenloopPath, 'fail', [
        'qwenloop ships with vibey: pip install vibey',
        'Or point the vibey.qwenloopPath setting at it.',
      ]),
    );
    const vibey = await this.program('vibey', this.deps.settings.raw.cliPath, 'warn', [
      'The Projects, Gates, Loops and Budgets views need vibey: pip install vibey',
      'Or point the vibey.cliPath setting at it.',
    ]);
    checks.push(vibey);
    if (vibey.status === 'pass') {
      checks.push(await this.vibeyCommands());
    }
    checks.push(
      await this.program('vibey-skills', this.deps.settings.raw.vibeySkillsPath, 'info', [
        'The Plugins menu needs vibey-skills, which ships with vibey.',
      ]),
    );
    const catalogue = await this.deps.catalogue();
    checks.push(
      catalogue.source === 'vibey'
        ? Doctor.check('loops', 'pass', `vibey loops: ${catalogue.loops.map((loop) => `${loop.loop} (${loop.engines.filter((engine) => engine.enabled).map((engine) => engine.engine_id).join(', ') || 'none switched on'})`).join('; ')}`)
        : Doctor.check('loops', 'warn', catalogue.notice as string),
    );
    checks.push(...(await this.ollama()));
    checks.push(this.environment());
    checks.push(
      this.deps.paidDeclared()
        ? Doctor.check('paid loop', 'info', 'Declared: paid engines may run when you choose paidloop, within your budgets.')
        : Doctor.check('paid loop', 'info', 'Not declared: everything runs on your own computer (sovereignloop).'),
    );
    return checks;
  }

  static render(checks: readonly DoctorCheck[]): string {
    const marks: Record<CheckStatus, string> = { pass: 'ok  ', warn: 'warn', fail: 'FAIL', info: 'info' };
    const lines: string[] = [];
    for (const check of checks) {
      lines.push(`[${marks[check.status]}] ${check.name}: ${check.detail}`);
      for (const step of check.fix ?? []) {
        lines.push(`         -> ${step}`);
      }
    }
    return lines.join('\n');
  }

  static failed(checks: readonly DoctorCheck[]): boolean {
    return checks.some((check) => check.status === 'fail');
  }

  private home(): DoctorCheck {
    const home = this.deps.settings.stormHome;
    const hits = this.deps.gate.inspect({ 'storm home': home.path });
    return hits.length === 0
      ? Doctor.check('storm home', 'pass', `${home.path} (from ${home.source}); a restart keeps it`)
      : Doctor.check('storm home', 'fail', `${home.path} is under ${hits[0]?.location}: ${hits[0]?.why}`, [
          'Choose a folder a restart keeps with the vibey.stormHome setting (or VIBEY_STORM_HOME).',
        ]);
  }

  /** Where the program was found, and what its --version says. */
  private async program(name: string, declared: string, missing: CheckStatus, fix: readonly string[]): Promise<DoctorCheck> {
    const located = this.deps.locator.locate(name, declared);
    if (located.path === undefined) {
      return Doctor.check(name, missing, `${located.error} (looked in ${located.source})`, fix);
    }
    const version = await this.deps.processes.run(located.path, ['--version'], { env: this.deps.environment, timeoutMs: 30_000 });
    const said = (version.stdout || version.stderr).trim().split('\n')[0] ?? '';
    return version.code === 0
      ? Doctor.check(name, 'pass', `${said} at ${located.path} (from ${located.source})`)
      : Doctor.check(name, missing, `${located.path} (from ${located.source}) did not answer --version: ${said || version.error || `exit ${version.code}`}`, fix);
  }

  private async vibeyCommands(): Promise<DoctorCheck> {
    const located = this.deps.locator.locate('vibey', this.deps.settings.raw.cliPath);
    const lacking: string[] = [];
    for (const command of Doctor.VIBEY_COMMANDS) {
      const help = await this.deps.processes.run(located.path as string, [command, '--help'], { env: this.deps.environment, timeoutMs: 30_000 });
      if (help.code !== 0) {
        lacking.push(command);
      }
    }
    return lacking.length === 0
      ? Doctor.check('vibey commands', 'pass', `vibey has ${Doctor.VIBEY_COMMANDS.join(', ')}`)
      : Doctor.check('vibey commands', 'warn', `this vibey lacks ${lacking.join(', ')}; they ship in vibey 3.0.0 (added after 2.1.0)`, [
          'Point vibey.cliPath at a newer vibey, or install one: pip install --upgrade vibey',
        ]);
  }

  private async ollama(): Promise<DoctorCheck[]> {
    const { settings, probe, advice, platform } = this.deps;
    const status = await probe.status(settings.model, settings.contextWindow);
    if (!status.reachable) {
      return [Doctor.check('Ollama', 'fail', `${status.root}: ${status.error}`, advice.advice(status, platform))];
    }
    const checks = [Doctor.check('Ollama', 'pass', `Ollama ${status.version} at ${status.root} (from ${settings.ollamaSource})`)];
    if (status.modelPresent !== true) {
      checks.push(Doctor.check('model', 'fail', advice.summary(status), advice.advice(status, platform)));
      return checks;
    }
    checks.push(Doctor.check('model', 'pass', `${settings.model} is downloaded (${status.modelSource}; from ${settings.modelSource})`));
    if (status.contextCheck === 'too-small') {
      checks.push(Doctor.check('context window', 'warn', advice.summary(status), advice.advice(status, platform)));
    } else if (status.contextCheck === 'ok') {
      checks.push(
        Doctor.check(
          'context window',
          'pass',
          `${settings.model} is loaded with ${status.loaded?.contextLength?.toLocaleString('en-US')} tokens; tasks plan for ${settings.contextWindow.toLocaleString('en-US')}`,
        ),
      );
    } else {
      checks.push(
        Doctor.check('context window', 'info', `unknown until ${settings.model} is loaded (it loads at the first task); tasks plan for ${settings.contextWindow.toLocaleString('en-US')} tokens`),
      );
    }
    const abilities = await probe.capabilities(settings.model);
    checks.push(
      abilities === undefined
        ? Doctor.check('model abilities', 'info', 'Ollama did not say what the model can do')
        : Doctor.check(
            'model abilities',
            'info',
            `${abilities.join(', ') || 'none listed'}${abilities.includes('vision') ? '' : '; no vision, so no image menu'}`,
          ),
    );
    return checks;
  }

  private environment(): DoctorCheck {
    const held = Object.keys(this.deps.environ)
      .filter((name) => this.deps.forbidden.forbids(name))
      .sort();
    return held.length === 0
      ? Doctor.check('environment', 'pass', 'nothing in your environment is held back from the model')
      : Doctor.check('environment', 'pass', `${held.length} variable(s) never reach a model: ${held.join(', ')}`);
  }

  private static check(name: string, status: CheckStatus, detail: string, fix?: readonly string[]): DoctorCheck {
    return fix === undefined || fix.length === 0 ? { name, status, detail } : { name, status, detail, fix };
  }
}
