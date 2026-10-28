// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What a share says, and what it never says. Pure, so the whole of it is tested. Declared by `interfaces/share-interface.ts`. */
import type { ShareComposerInterface, ShareableProject, SharedText } from './interfaces/share-interface';

export class ShareComposer implements ShareComposerInterface {
  /** The longest name a share carries: the hub accepts 64, so this is a guard, not a limit. */
  static readonly NAME_LIMIT = 64;

  compose(project: ShareableProject): SharedText {
    // Each field is read by name: spreading the object would let anything on it leave the device.
    const name = String(project.name).trim().slice(0, ShareComposer.NAME_LIMIT);
    const phase = String(project.phase).trim();
    const cycle = String(project.cycle).trim();
    const where = cycle === '' ? phase : `${phase}, ${cycle.charAt(0).toLowerCase()}${cycle.slice(1)}`;
    return {
      title: `${name} on krypton`,
      message: `${name} is in ${where}.`,
    };
  }
}
