* **krypton desktop starts this computer's hub, and never stops it on quit (#1186):** opening the app with no hub running
  runs `vibey hub start` in the background (a setting, on by default, and only for *This computer*), and Start, Stop and
  Status are in the header menu, the Settings page and the tray menu. A failed start is a note in the connection status,
  never a pop-up, and the offline banner says what krypton is doing instead of "run `vibey serve`".
