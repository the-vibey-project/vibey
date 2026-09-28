---
id: skill-4-configuring-vim-and-neovim-8cb86ecfc9
purpose: 4 configuring vim and neovim
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-choosing-vim-neovim-and-emacs/SKILL.md
requires: ["skill-3-vim-s-actual-model-22c3d218fb"]
links: ["skill-5-emacs-2eeefb2f8f"]
---

## §4. Configuring Vim and Neovim

```
VIM        ~/.vimrc, Vimscript (⚠️ Vim9script in Vim 9)
⚠️ NEOVIM  ~/.config/nvim/init.lua, LUA. ⚠️ Faster, saner, better tooling
```
**⚠️ Neovim's structural advantages over Vim** (§24.2 → `editor-reference`): ⚠️ **a built-in LSP client, built-in
Tree-sitter, Lua config and plugins, real async, and a plugin ecosystem that increasingly
targets Neovim exclusively.**
**⚠️ The modern Neovim stack**: **`lazy.nvim` (plugin manager), `nvim-lspconfig` +
`mason.nvim` (language servers), `nvim-treesitter`, `telescope.nvim` (fuzzy finding),
`gitsigns.nvim`.**
**⚠️ Distributions — LazyVim, NvChad, AstroNvim, kickstart.nvim** — ⚠️ **flatten the
on-ramp enormously, and the tradeoff is that you inherit someone else's decisions and
debug their abstractions.** **`kickstart.nvim` is the honest middle: a single readable
file you're expected to modify.**
**⚠️ The config trap worth naming**: ⚠️ **time spent configuring the editor is not time
spent working**, **and "endless config tinkering" is a recognized failure mode for
exactly the personality that enjoys vim.** **Set a budget.**

---
