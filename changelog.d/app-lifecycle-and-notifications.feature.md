* **The mobile and web app can start and steer a project, answer the design interview, and notify you:** a Start screen
  (name and a sentence of intake; the host chooses the folder), Resume, Pause and Unwind on each project card (Unwind
  shows what it would cancel first, asks for a reason, and re-checks it is you with Face ID, Touch ID or the passcode),
  and an "Accept the suggested answers" button for the design interview, which used to say "answer this on the host".
  The app now uses `expo-notifications`: while it is open or just in the background it tells you when a project needs
  you, when a spending question appears, and when a project finishes, honoring the switches in Settings. A closed app
  hears nothing yet: that needs the hub to push.
