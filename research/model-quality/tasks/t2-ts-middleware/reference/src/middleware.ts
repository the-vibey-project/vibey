import { response } from "./http.ts";
import type { Handler, Request, Response } from "./http.ts";

export type Middleware = (req: Request, next: Handler) => Response;

export function compose(middlewares: Middleware[], handler: Handler): Handler {
  return middlewares.reduceRight<Handler>(
    (next, middleware) => (req) => middleware(req, next),
    handler,
  );
}

export function requireHeader(name: string, status = 401): Middleware {
  const wanted = name.toLowerCase();
  return (req, next) => {
    for (const [key, value] of Object.entries(req.headers)) {
      if (key.toLowerCase() === wanted && value !== "") {
        return next(req);
      }
    }
    return response(status, "missing header: " + name);
  };
}

export function addResponseHeader(name: string, value: string): Middleware {
  return (req, next) => {
    const res = next(req);
    return { ...res, headers: { ...res.headers, [name]: value } };
  };
}
