* **Krypton no longer installs the vulnerable `node-forge` release:** the app lockfile now
  resolves the Expo CLI transitive dependency to `node-forge` 1.4.2, and the expired,
  obsolete advisory exception has been removed. The high-severity advisory gate now passes
  without an exception for the package.
