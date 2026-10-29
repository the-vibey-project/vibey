* **The desktop `hub-client` test no longer fails the `krypton desktop (ubuntu)` job on leaked TLS tasks:** LeakSanitizer
  reported 202 bytes in 4 allocations, errors created in glib-networking worker threads by TLS handshake and close tasks
  that the test never let the main loop collect. The pinned-pairing test now releases its clients before it stops the hub,
  and a stopped TLS hub runs the main loop until it is quiet. Leak detection stays on; no suppression was added.
