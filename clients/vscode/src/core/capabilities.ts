// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Menus for images, files, pasting and plugins appear only where the capability is verified.
 *
 * An engine's capabilities come from `vibey loops --json`, each backed by its descriptor's
 * evidence; `null` is unknown and earns no menu. An image menu also needs the model to see:
 * for a local model that is Ollama's own answer (POST /api/show `capabilities` includes
 * `vision`; gpt-oss:20b reports completion, tools and thinking, so it has none). Pasting text
 * always works: a plan is text.
 *
 * Plugins mean vibey-skills context packets, compiled by the family's own `vibey-skills
 * packet` exactly as vibey's `skills_context.py` asks for them, from the plugins in the
 * repository's `.claude-plugin/marketplace.json`: no third-party picker (the dogfood rule).
 * Declared by `interfaces/capabilities-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import type { EngineCapabilities } from '@vibey/core';
import type {
  CapabilitiesInterface,
  CapabilityMenu,
  MarketplacePlugin,
  SkillsContextInterface,
  SkillsMarketplaceInterface,
  SkillsPacket,
} from '@vibey/core';
import type { Environment, ProcessRunnerInterface } from '@vibey/core';
import type { IdSourceInterface } from '@vibey/core';

export class Capabilities implements CapabilitiesInterface {
  menu(
    engine: EngineCapabilities,
    tier: 'local' | 'paid',
    modelCapabilities: readonly string[] | undefined,
  ): CapabilityMenu {
    const notes: string[] = [];
    const sees = tier === 'paid' || (modelCapabilities?.includes('vision') ?? false);
    if (engine.images === true && !sees) {
      notes.push(
        modelCapabilities === undefined
          ? "No image menu: Ollama has not said whether the model can see images."
          : `No image menu: the model reports ${modelCapabilities.join(', ') || 'no capabilities'}, not vision.`,
      );
    }
    if (engine.images !== true) {
      notes.push(engine.images === null ? 'No image menu: whether this engine takes images is not verified.' : 'No image menu: this engine does not take images.');
    }
    const plugins = engine.plugins === 'skills-context' || engine.plugins === 'claude-plugins' ? engine.plugins : undefined;
    return {
      attachImage: engine.images === true && sees,
      pasteImage: engine.paste_images === true && sees,
      attachFile: engine.files === true,
      pasteText: true,
      ...(plugins === undefined ? {} : { plugins }),
      notes,
    };
  }
}

export class SkillsMarketplace implements SkillsMarketplaceInterface {
  static readonly FILE = path.join('.claude-plugin', 'marketplace.json');

  plugins(repository: string): readonly MarketplacePlugin[] {
    let parsed: unknown;
    try {
      parsed = JSON.parse(fs.readFileSync(path.join(repository, SkillsMarketplace.FILE), 'utf8'));
    } catch {
      return [];
    }
    const plugins = (parsed as { plugins?: unknown }).plugins;
    if (!Array.isArray(plugins)) {
      return [];
    }
    return plugins
      .filter(
        (plugin): plugin is Record<string, unknown> =>
          typeof plugin === 'object' && plugin !== null && typeof (plugin as { name?: unknown }).name === 'string',
      )
      .map((plugin) => ({
        name: plugin.name as string,
        description: typeof plugin.description === 'string' ? plugin.description : '',
        ...(typeof plugin.category === 'string' ? { category: plugin.category } : {}),
      }));
  }
}

/**
 * `vibey-skills` as vibey's `VibeySkillsContextCompiler` drives it: build or reuse a local
 * index, write a packet request, and ask for one packet within a token budget.
 */
export class SkillsContext implements SkillsContextInterface {
  /** vibey's own bounds for a packet budget (skills_context.py). */
  static readonly MIN_BUDGET = 1000;
  static readonly MAX_BUDGET = 32000;

  constructor(
    private readonly runner: ProcessRunnerInterface,
    private readonly executable: string,
    private readonly environment: Environment,
    /** Where the index lives, and where each packet's files go, on durable storage. */
    private readonly directory: string,
    private readonly budget: number,
    private readonly ids: IdSourceInterface,
    private readonly timeoutMs = 120_000,
  ) {}

  async packet(request: {
    readonly title: string;
    readonly objective: string;
    readonly plugins: readonly string[];
  }): Promise<SkillsPacket> {
    const budget = Math.min(Math.max(this.budget, SkillsContext.MIN_BUDGET), SkillsContext.MAX_BUDGET);
    const index = path.join(this.directory, 'index');
    const work = path.join(this.directory, 'packets', this.ids.uuid());
    fs.mkdirSync(work, { recursive: true });
    const indexError = await this.ensureIndex(index);
    if (indexError !== undefined) {
      return { ok: false, error: indexError };
    }
    const requestPath = path.join(work, 'request.json');
    const packetPath = path.join(work, 'packet.md');
    const manifestPath = path.join(work, 'packet.json');
    fs.writeFileSync(
      requestPath,
      `${JSON.stringify({
        schema_version: 1,
        title: request.title,
        objective: request.objective,
        phase: 'build',
        job_kind: 'vscode.ask',
        commands: [],
        maximum_context_tokens: budget,
        ranking_mode: 'deterministic',
        ...(request.plugins.length === 0 ? {} : { required_plugins: [...request.plugins] }),
      })}\n`,
    );
    const result = await this.run([
      'packet',
      '--request',
      requestPath,
      '--index',
      index,
      '--budget',
      String(budget),
      '--output',
      packetPath,
      '--manifest',
      manifestPath,
    ]);
    // vibey reads 0 and 2 as answers (2: a packet with less than was asked for).
    if (result.code !== 0 && result.code !== 2) {
      return { ok: false, error: `vibey-skills packet failed: ${(result.stderr || result.error || `exit ${result.code}`).trim()}` };
    }
    let status = 'unknown';
    try {
      const manifest: unknown = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      const said = (manifest as { status?: unknown }).status;
      status = typeof said === 'string' ? said : status;
    } catch {
      status = 'no manifest';
    }
    const markdown = fs.existsSync(packetPath) ? fs.readFileSync(packetPath, 'utf8') : '';
    return { ok: true, markdown, status, manifest: manifestPath, plugins: request.plugins };
  }

  private async ensureIndex(index: string): Promise<string | undefined> {
    if (fs.existsSync(path.join(index, 'manifest.json')) && fs.existsSync(path.join(index, 'index.sqlite3'))) {
      const inspect = await this.run(['index', 'inspect', index, '--json']);
      if (inspect.code === 0) {
        return undefined;
      }
    }
    const build = await this.run(['index', 'build', '--output', index]);
    return build.code === 0
      ? undefined
      : `vibey-skills could not build its index: ${(build.stderr || build.error || `exit ${build.code}`).trim()}`;
  }

  private run(args: readonly string[]): ReturnType<ProcessRunnerInterface['run']> {
    return this.runner.run(this.executable, args, { cwd: this.directory, env: this.environment, timeoutMs: this.timeoutMs });
  }
}
