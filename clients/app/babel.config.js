// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Project-wide, so @vibey/core and the design tokens (outside this folder) compile the same way.
module.exports = function (api) {
  api.cache(true);
  return { presets: ['babel-preset-expo'] };
};
