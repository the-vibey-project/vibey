---
id: skill-domain-3-frontend-security-react-and-blazor-wasm-f10ec2aa95
purpose: domain 3 frontend security react and blazor wasm
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: ["skill-domain-2-api-security-net-8-web-api-13c702198c"]
links: ["skill-domain-4-data-layer-security-cosmosdb-postgresql-databricks-156b32d5f8"]
---

## DOMAIN 3: FRONTEND SECURITY (REACT AND BLAZOR WASM)

### Foundational — Token Management and XSS Prevention

**Never store tokens in `localStorage`** — any XSS vulnerability enables trivial theft via
`localStorage.getItem('token')`. Use `sessionStorage` (per-tab isolation, auto-clears on close).

**Axios interceptor for automatic token attachment and silent refresh:**
```typescript
// apiClient.ts
import axios from 'axios';
import { msalInstance } from './authConfig';
import { InteractionRequiredAuthError } from '@azure/msal-browser';

const apiClient = axios.create({ baseURL: 'https://api.example.com' });

apiClient.interceptors.request.use(async (config) => {
  const account = msalInstance.getActiveAccount();
  if (!account) throw new Error('No active account');
  try {
    const response = await msalInstance.acquireTokenSilent({
      scopes: ['api://your-api-client-id/.default'], account,
    });
    config.headers.Authorization = `Bearer ${response.accessToken}`;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect({
        scopes: ['api://your-api-client-id/.default'],
      });
    }
  }
  return config;
});
```

**Four vectors that bypass React's auto-escaping protection:**
1. `dangerouslySetInnerHTML` without sanitization
2. `href` with `javascript:` protocol
3. Direct DOM manipulation via `ref.current.innerHTML`
4. `eval()` with user input

**DOMPurify SafeHTML wrapper** (npm: `dompurify`, `@types/dompurify`):
```tsx
import DOMPurify from 'dompurify';
export function SafeHTML({ html }: { html: string }) {
  const sanitized = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a'],
    FORBID_TAGS: ['script', 'style', 'iframe'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  });
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
```

### Intermediate — Blazor WASM Constraints and Protected Routes

**Blazor WASM fundamental security constraint:** Everything runs client-side. All .NET assemblies
are downloadable and decompilable with ILSpy. All `[Authorize]` attributes and `AuthorizeView`
components are cosmetic — **the server API must re-validate every request**. Never put secrets,
sensitive business logic, or intellectual property in Blazor WASM code.

**Blazor WASM auth routing:**
```razor
<!-- App.razor -->
<CascadingAuthenticationState>
    <Router AppAssembly="@typeof(Program).Assembly">
        <Found Context="routeData">
            <AuthorizeRouteView RouteData="@routeData" DefaultLayout="@typeof(MainLayout)">
                <NotAuthorized>
                    @if (context.User.Identity?.IsAuthenticated != true)
                    { <RedirectToLogin /> }
                    else
                    { <p>You are not authorized.</p> }
                </NotAuthorized>
            </AuthorizeRouteView>
        </Found>
    </Router>
</CascadingAuthenticationState>
```

**React protected route with role checking:**
```tsx
function ProtectedRoute({ allowedRoles }: { allowedRoles?: string[] }) {
  const isAuthenticated = useIsAuthenticated();
  const { accounts } = useMsal();
  const location = useLocation();

  if (!isAuthenticated)
    return <Navigate to="/login" state={{ from: location }} replace />;
  if (allowedRoles?.length) {
    const userRoles = (accounts[0]?.idTokenClaims as any)?.roles ?? [];
    if (!allowedRoles.some(role => userRoles.includes(role)))
      return <Navigate to="/unauthorized" replace />;
  }
  return <Outlet />;
}
```

Both React and Blazor role-based UI rendering are UX features only. The API `[Authorize]` is the
real security boundary.

### Advanced — CSP Headers, Dependency Security, SRI

**Content Security Policy for React/Vite:**
```typescript
// vite.config.ts
export default defineConfig({
  build: { assetsInlineLimit: 0 }, // Prevent inline scripts that bypass CSP
  server: {
    headers: {
      'Content-Security-Policy': [
        "default-src 'self'",
        "script-src 'self'",
        "connect-src 'self' https://login.microsoftonline.com https://api.example.com",
        "img-src 'self' data: https:",
        "frame-ancestors 'none'",
      ].join('; '),
    },
  },
});
```

**Production CSP (served by .NET backend):**
```
default-src 'self';
script-src 'self' 'nonce-{SERVER_GENERATED}' 'strict-dynamic';
style-src 'self' 'nonce-{SERVER_GENERATED}';
connect-src 'self' https://login.microsoftonline.com https://graph.microsoft.com;
frame-ancestors 'none';
upgrade-insecure-requests;
```

**Dependency security automation:**
```xml
<!-- .csproj — NuGet audit on every build -->
<PropertyGroup>
    <NuGetAudit>true</NuGetAudit>
    <NuGetAuditMode>all</NuGetAuditMode>
    <NuGetAuditLevel>low</NuGetAuditLevel>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
</PropertyGroup>
```

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule: { interval: "weekly" }
  - package-ecosystem: "nuget"
    directory: "/backend"
    schedule: { interval: "weekly" }
  - package-ecosystem: "pip"
    directory: "/databricks"
    schedule: { interval: "weekly" }
```

---
