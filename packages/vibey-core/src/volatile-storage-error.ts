// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The refusal to keep work on storage the operating system empties (sub-doctrine 10.h, ADR-0057). */
import type { VolatileHit } from './interfaces/storage-interface';

/** Raised by the gate. `exitCode` is EX_CONFIG from sysexits.h, as the storm tools use. */
export class VolatileStorageError extends Error {
  static readonly EXIT_CODE = 78;

  constructor(readonly hits: readonly VolatileHit[]) {
    super(VolatileStorageError.describe(hits));
    this.name = 'VolatileStorageError';
  }

  private static describe(hits: readonly VolatileHit[]): string {
    const lines = ['refused: this work would be kept on storage the operating system empties.'];
    for (const hit of hits) {
      const shown = hit.resolved === hit.path ? hit.path : `${hit.path} -> ${hit.resolved}`;
      lines.push(`  ${hit.name}: ${shown}`);
      lines.push(`    under ${hit.location}: ${hit.why}`);
    }
    lines.push(
      'Choose a folder a restart keeps with the vibey.stormHome setting (or --storm-home, or VIBEY_STORM_HOME). ' +
        'Anything not committed there is lost at the next restart. Sub-doctrine 10.h; ADR-0057.',
    );
    return lines.join('\n');
  }
}
