// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Which extra menus an engine earns (images, files, paste, plugins), and the plugins behind one. */
import type { EngineCapabilities } from './catalogue-interface';

/**
 * The plugin systems `vibey loops --json` reports, as vibey's `PluginSystem` names them
 * (domain/engine.py): vibey-skills context packets, Claude Code's own plugins, or the vibey
 * bundle the local runner (gptossloop, qwenloop) takes in their place (ADR-0092, ADR-0103).
 */
export type PluginSystem = 'skills-context' | 'claude-plugins' | 'vibey-bundle';

export interface CapabilityMenu {
  readonly attachImage: boolean;
  readonly pasteImage: boolean;
  readonly attachFile: boolean;
  readonly pasteText: boolean;
  /** Which plugin menu, if any: the engine's plugin system, when it is one vibey reports. */
  readonly plugins?: PluginSystem;
  /** Why a menu is missing, for a person who looks for it. */
  readonly notes: readonly string[];
}

export interface CapabilitiesInterface {
  menu(
    engine: EngineCapabilities,
    tier: 'local' | 'paid',
    modelCapabilities: readonly string[] | undefined,
  ): CapabilityMenu;
}

export interface MarketplacePlugin {
  readonly name: string;
  readonly description: string;
  readonly category?: string;
}

export interface SkillsMarketplaceInterface {
  /** The plugins in `<repository>/.claude-plugin/marketplace.json`; none when there is no file. */
  plugins(repository: string): readonly MarketplacePlugin[];
}

export type SkillsPacket =
  | { readonly ok: true; readonly markdown: string; readonly status: string; readonly manifest: string; readonly plugins: readonly string[] }
  | { readonly ok: false; readonly error: string };

export interface SkillsContextInterface {
  /** A context packet for a task from `vibey-skills packet`, the family's own compiler. */
  packet(request: { readonly title: string; readonly objective: string; readonly plugins: readonly string[] }): Promise<SkillsPacket>;
}
