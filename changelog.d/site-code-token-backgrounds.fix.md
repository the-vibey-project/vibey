* **docs:** code on the documentation site no longer prints pale text on a pale band. The
  site paints code blocks dark but kept the light highlight.js theme's token backgrounds, so a
  block highlight.js read as a diff (lines starting "- ") showed pale pink text on pale pink,
  as in the self-hosted surfaces topology. Token backgrounds are now transparent everywhere,
  and that diagram is marked as plain text.
