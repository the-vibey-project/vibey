// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// @vibey/core is read from its source, and it re-exports the generated design tokens, so Metro
// watches both folders outside this app (ADR-0067: never a copy of the tokens).
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const root = path.resolve(__dirname, '../..');
const config = getDefaultConfig(__dirname);
config.watchFolders = [path.join(root, 'packages/vibey-core/src'), path.join(root, 'design/dist/ts')];
config.resolver.extraNodeModules = { '@vibey/core': path.join(root, 'packages/vibey-core/src') };
config.resolver.nodeModulesPaths = [path.join(__dirname, 'node_modules')];
module.exports = config;
