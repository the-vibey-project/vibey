import { response } from "./http.ts";
import type { Handler } from "./http.ts";

export function createApp(routes: Record<string, Handler>): Handler {
  return (req) => {
    const handler = routes[`${req.method} ${req.path}`];
    if (handler === undefined) {
      return response(404, "not found");
    }
    return handler(req);
  };
}
