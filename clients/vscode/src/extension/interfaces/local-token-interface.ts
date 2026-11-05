// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Interface for reading the host's hub token on the local machine.
 * The token file is created on first run (0600) and proves the caller is the host account.
 */
export interface LocalHubTokenInterface {
  tokenPath(platform?: string, home?: string): string;
  readToken(customPath?: string): string | undefined;
}
