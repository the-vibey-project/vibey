// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The krypton app's Babel configuration. Expo's Babel reads `babel.config.js`; TypeScript is the
// only authored form (sub-doctrine 9.f), so scripts/typescript_artifacts.py compiles this file
// to it. `export =` is what makes the compiled file `module.exports = config`.
interface BabelApi {
  cache(enabled: boolean): void;
}

const config = (api: BabelApi): { presets: string[] } => {
  api.cache(true);
  return { presets: ['babel-preset-expo'] };
};

export = config;
