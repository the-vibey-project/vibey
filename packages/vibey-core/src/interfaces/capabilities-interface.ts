// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Which extra menus an engine earns (images, files, paste, plugins), and the plugins behind one. */
import type { EngineCapabilities } from './catalogue-interface';

export interface CapabilityMenu {
  readonly attachImage: boolean;
  readonly pasteImage: boolean;
  readonly attachFile: boolean;
  readonly pasteText: boolean;
  /** Which plugin menu, if any: vibey-skills context packets, or Claude Code's own plugins. */
  readonly plugins?: 'skills-context' | 'claude-plugins';
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
