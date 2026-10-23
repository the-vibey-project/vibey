* **The krypton mobile app builds again:** `react-native-reanimated` and `react-native-worklets` are pinned to the
  versions Expo SDK 57 declares (4.5.1 and 0.10.1). They were only transitive, so a lockfile re-derivation could
  and did resolve Reanimated 4.2.2, which does not support React Native 0.86 and failed the iOS `pod install`.
  `expo-camera` and `expo-notifications` move to the patch versions the SDK expects, so `expo-doctor` is clean.
