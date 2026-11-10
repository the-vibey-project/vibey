`src/http.ts` defines `Request`, `Response`, `Handler` (`(req) => Response`) and a
`response(status, body, headers?)` helper. `src/app.ts` has `createApp(routes)`, which looks up
`"METHOD /path"` in a routes object and answers 404 `"not found"` otherwise. Add middleware.

1. Create `src/middleware.ts` exporting:
   - `type Middleware = (req: Request, next: Handler) => Response`.
   - `compose(middlewares: Middleware[], handler: Handler): Handler`. The first middleware in the
     array is the outermost: it sees the request first and the response last. A middleware that
     does not call `next` short-circuits everything after it. With an empty array `compose`
     behaves like `handler`.
   - `requireHeader(name: string, status = 401): Middleware`. If the request has a header called
     `name` (header names are compared case-insensitively) whose value is not the empty string,
     it calls `next(req)`. Otherwise it does not call `next` and returns
     `response(status, "missing header: " + name)`, using `name` exactly as given.
   - `addResponseHeader(name: string, value: string): Middleware`. It calls `next(req)` and returns
     a copy of that response with the header added to its `headers`, replacing any header with the
     same exact name. It must not modify the response object it received.
2. Change `createApp` to `createApp(routes, middlewares = [])`. The middlewares wrap the whole
   route lookup, so they also see the 404 response.
3. `createApp` must catch anything thrown by a middleware or a handler and answer
   `response(500, "internal error")`. The catch wraps the entire composed chain, so
   middlewares do not touch that 500 response.
4. Without middlewares `createApp` behaves exactly as before.
