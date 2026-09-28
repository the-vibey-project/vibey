---
id: skill-android-kotlin-jetpack-compose-34507e7782
purpose: android kotlin jetpack compose
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-native-platforms/SKILL.md
requires: ["skill-ios-swift-swiftui-555b4d2b3d"]
links: []
---

## Android — Kotlin / Jetpack Compose

- **Concurrency:** Kotlin Coroutines + Flow + structured concurrency (`viewModelScope`,
  `StateFlow`/`SharedFlow`).
- **Recommended Compose architecture is UDF** ("state flows down, events flow up") with **state
  hoisting** to the lowest common parent: a single immutable UI-state data class exposed as
  `StateFlow`, collected via `collectAsStateWithLifecycle()` (from
  `androidx.lifecycle:lifecycle-runtime-compose`). **MVVM** is Google's baseline; **MVI** adds a
  stricter reducer `(oldState, event) -> newState` + intents + one-off effects
  (`Channel`/`SharedFlow`) that aligns with Compose's declarative model.

### Compose side-effect APIs

| API | Purpose |
|---|---|
| `LaunchedEffect` | key-scoped coroutine |
| `rememberCoroutineScope` | launch from callbacks |
| `rememberUpdatedState` | fresh value without restart |
| `DisposableEffect` | `onDispose` cleanup |
| `SideEffect` | post-recomposition publish to non-Compose objects |
| `derivedStateOf` | recompute only when result changes |
| `produceState` | non-Compose → Compose state |
| `snapshotFlow` | Compose State → Flow |

### DI & Jetpack libraries

- **Hilt** (built on Dagger, compile-time DI): `androidx.hilt 1.3.0` (Sep 10, 2025; `hiltViewModel()`
  moved to `androidx.hilt:hilt-lifecycle-viewmodel-compose`, targets Kotlin 2.0/KSP2).
  `@HiltViewModel` + constructor `@Inject`. Scopes: `@Singleton` (SingletonComponent) →
  `@ActivityRetainedScoped` (survives config changes) → `@ViewModelScoped`. Shared dependencies
  across ViewModels should be `@ActivityRetainedScoped` or `@Singleton`.
- **Room 2.8.4** (KSP; `ksp("androidx.room:room-compiler:2.8.4")`). **Room 3.0** (`androidx.room3`,
  3.0.0-alpha01, March 2026) is a KMP rewrite — KSP-only, coroutine-first (suspend DAOs), still alpha.
- **DataStore 1.1.7** (Preferences vs Proto) — async, Flow-based SharedPreferences replacement;
  **no encrypted DataStore exists yet**.
- **WorkManager** for deferrable guaranteed work (`@HiltWorker` + `HiltWorkerFactory`).
- **Navigation Compose** with `hiltViewModel()`.

### Android security

- **Jetpack Security Crypto (`androidx.security:security-crypto`) is DEPRECATED** at 1.1.0-alpha07
  (April 2025) — all APIs (incl. `EncryptedSharedPreferences`/`EncryptedFile`) deprecated "in favour
  of … direct use of Android Keystore." Migrate to direct **Android Keystore** or community forks
  (Ackee Guardian, `dev.spght:encryptedprefs`).
- Android Keystore **TEE** vs **StrongBox** (HSM, API 28+) with **key attestation**; verify
  `isInsideSecureHardware()`.
- **BiometricPrompt + `CryptoObject`** ties crypto operations to biometric auth.
- Build with Gradle + KSP. (Confirm the current `androidx.biometric:biometric` version before pinning.)

See `mobile-security` for the cross-platform secure-storage, comms, and MFA baseline.
