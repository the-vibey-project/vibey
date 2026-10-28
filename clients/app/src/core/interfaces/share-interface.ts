// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What leaves the device when a person shares a project (#1698). */

export interface SharedText {
  /** The subject line a share sheet offers (a mail subject, a message title). */
  readonly title: string;
  /** The text itself. */
  readonly message: string;
}

/** The only fields of a project card a share may read: nothing else can be named in it. */
export interface ShareableProject {
  readonly name: string;
  readonly phase: string;
  /** "Cycle 2 of 5", or empty. */
  readonly cycle: string;
}

export interface ShareComposerInterface {
  /**
   * The text for a project: its name, its phase and its cycle, in a sentence. The composer
   * reads those three fields by name and nothing else, so an id, a gate, a path, a cost or a
   * token that happens to be on the object it is handed cannot reach the message.
   */
  compose(project: ShareableProject): SharedText;
}
