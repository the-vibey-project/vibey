`src/router.ts` has a `Router` whose `add(method, path, handler)` registers a route and
`dispatch(method, path)` returns the handler's string result, or `undefined` when no route
matches. Today it only matches paths that are exactly equal. Add path parameters.

1. Create `src/pattern.ts` exporting `matchPath(pattern: string, path: string): Params | null`
   (`Params` is the existing type in `src/router.ts`; import it with `import type`). It returns
   the captured parameters, or `null` when the path does not match.
2. Both strings start with `/`. Split them on `/`. A single trailing slash on either is ignored,
   so `/users/` and `/users` match each other, and `/` has no segments.
3. A pattern segment `:name` matches exactly one non-empty path segment and captures it under
   `name`, passed through `decodeURIComponent`. If decoding throws, the result is `null`.
4. A final pattern segment `*` matches one or more remaining path segments and captures them
   under the key `"*"`, joined with `/` and not decoded. It does not match zero segments.
5. Every other pattern segment must equal the path segment exactly (case-sensitive), and the
   number of segments must otherwise be equal. A literal pattern with no captures returns `{}`.
6. In `Router.dispatch`, a route whose path is exactly equal to the requested path still wins
   first, as today, and its handler receives `{}`. If there is none, try the routes for that
   method in registration order with `matchPath`; the first match wins and its handler receives
   the captured params. Method comparison stays case-insensitive. No match still gives
   `undefined`.
