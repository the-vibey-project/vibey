---
id: skill-azure-integration-auth-d34b7603cd
purpose: azure integration auth
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-react-native/SKILL.md
requires: ["skill-expo-eas-69db33dbb0"]
links: ["skill-crash-observability-7be21867b0"]
---

## Azure integration (auth)

- **`react-native-msal`** wraps MSAL for iOS/Android; supports Entra ID and Azure AD B2C /
  External ID.
- iOS config: `CFBundleURLSchemes` = `msauth.$(PRODUCT_BUNDLE_IDENTIFIER)`;
  `LSApplicationQueriesSchemes` = `msauthv2`, `msauthv3`. MSAL uses `ASWebAuthenticationSession`.
- Android config: `BrowserTabActivity` intent filter.
- Use **OAuth 2.0 Authorization Code + PKCE** via the system browser (AppAuth pattern) —
  implicit flow is prohibited; refresh tokens must rotate. **Validate RS256 JWTs server-side**
  against the tenant JWKS endpoint. (See `mobile-security` for full auth/MFA detail.)
