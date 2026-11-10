import { matchPath } from "./pattern.ts";

export type Params = Record<string, string>;
export type RouteHandler = (params: Params) => string;

interface Route {
  method: string;
  path: string;
  handler: RouteHandler;
}

export class Router {
  private routes: Route[] = [];

  add(method: string, path: string, handler: RouteHandler): void {
    this.routes.push({ method: method.toUpperCase(), path, handler });
  }

  dispatch(method: string, path: string): string | undefined {
    const wanted = method.toUpperCase();
    const candidates = this.routes.filter((route) => route.method === wanted);
    for (const route of candidates) {
      if (route.path === path) {
        return route.handler({});
      }
    }
    for (const route of candidates) {
      const params = matchPath(route.path, path);
      if (params !== null) {
        return route.handler(params);
      }
    }
    return undefined;
  }
}
