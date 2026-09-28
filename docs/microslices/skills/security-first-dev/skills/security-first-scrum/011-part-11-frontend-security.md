---
id: skill-part-11-frontend-security-3693f41d54
purpose: part 11 frontend security
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-10-api-security-net-8-39282394b9"]
links: ["skill-part-12-data-layer-security-984d1a5813"]
---

## PART 11: FRONTEND SECURITY

### React XSS Prevention

Four vectors that bypass React's auto-escaping — never use these unsafely:
1. `dangerouslySetInnerHTML` without sanitization — always sanitize with DOMPurify
2. `href` with `javascript:` protocol — validate URLs before use
3. Direct DOM manipulation via `ref.current.innerHTML` — avoid; use React state
4. `eval()` with user input — never

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

### Protected Routes

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

This is a UX gate, not a security boundary. The API endpoint is the real boundary.

### Content Security Policy (Vite)

```typescript
// vite.config.ts
export default defineConfig({
  build: { assetsInlineLimit: 0 }, // Prevent inline scripts that bypass CSP
  server: {
    headers: {
      'Content-Security-Policy': [
        "default-src 'self'", "script-src 'self'",
        "connect-src 'self' https://login.microsoftonline.com https://api.example.com",
        "img-src 'self' data: https:", "frame-ancestors 'none'",
      ].join('; '),
    },
  },
});
```

---
