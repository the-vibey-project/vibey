import { response } from "./http.ts";
import type { Handler } from "./http.ts";
import { compose } from "./middleware.ts";
import type { Middleware } from "./middleware.ts";

export function createApp(
  routes: Record<string, Handler>,
  middlewares: Middleware[] = [],
): Handler {
  const dispatch: Handler = (req) => {
    const handler = routes[`${req.method} ${req.path}`];
    if (handler === undefined) {
      return response(404, "not found");
    }
    return handler(req);
  };
  const chain = compose(middlewares, dispatch);
  return (req) => {
    try {
      return chain(req);
    } catch {
      return response(500, "internal error");
    }
  };
}
