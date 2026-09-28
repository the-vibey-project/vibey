---
id: skill-3-vim-s-actual-model-22c3d218fb
purpose: 3 vim s actual model
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-choosing-vim-neovim-and-emacs/SKILL.md
requires: ["skill-2-nano-047effbd42"]
links: ["skill-4-configuring-vim-and-neovim-8cb86ecfc9"]
---

## §3. ⚠️ Vim's Actual Model

**⚠️ The thing to understand: vim is a LANGUAGE with a grammar, not a set of shortcuts.**
```
⚠️ OPERATOR + [COUNT] + MOTION-OR-TEXT-OBJECT
   d (delete) · c (change) · y (yank) · > (indent) · gu/gU (case) · = (format)
```
**⚠️ Motions**: **`w` word, `b` back, `e` end, `0` line start, `^` first non-blank,
`$` end, `gg`/`G` file start/end, `}`/`{` paragraph, `f<char>`/`t<char>` find/till on
line, `%` matching bracket.**
**⚠️ TEXT OBJECTS are the part people miss and the part that pays:**
```
⚠️ i = "inner", a = "a/around" (includes delimiters)
   ciw  change inner word          ci"  change inside quotes
   ci(  change inside parens       dap  delete a paragraph
   dit  delete inside HTML tag     ya{  yank a block with braces
⚠️ These work from ANYWHERE in the object — you don't position first
```
⚠️ **Learn the composition and you get combinations you were never taught.** **`d` +
`i` + `(` is not a memorized shortcut — it's the grammar producing a result.**

**⚠️ Modes**: **Normal (default — ⚠️ vim is a normal-mode editor that occasionally lets you
insert), Insert, Visual (char/line/block), Command-line, Replace.**
**⚠️ Registers**: ⚠️ **`"a`–`"z` named, `""` unnamed (the default), `"0` last yank
(survives deletes — which is the fix for "I deleted something and lost my copy"), `"+`
system clipboard, `"%` filename.**
**⚠️ Survival minimum for the server-at-3am case:**
```
i  insert    Esc  normal    :w  write    :q  quit    :wq  both
⚠️ :q!  quit without saving  ← THE one people need and don't know
dd  delete line    u  undo    Ctrl-r  redo    /text  search    n  next
```
**⚠️ Macros are underused**: **`qa` record into register a, `q` stop, `@a` play, `@@`
repeat, `10@a` ten times.** ⚠️ **A recorded macro beats a hand-written regex for most
repetitive edits, and it's testable one step at a time.**
**⚠️ The dot command `.` repeats the last change** — **and structuring edits so `.` can
repeat them is the actual expert skill.**

---
