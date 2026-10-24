* **An advisory whose fix no dependent can take no longer blocks CI forever:** an exception may declare
  `fix_unreachable`, which lets it stand although a patched release exists when no package that depends on it accepts
  that release (a major above every dependent's range). The gate checks itself that the package is dev-only in the
  lockfile and refuses the key for one that ships; the 30-day expiry still applies. Used for `@azure/msal-node`
  (GHSA-xcx6-jx8p-x3h5), reached only through `@vscode/vsce`, whose every release pins the vulnerable major.
