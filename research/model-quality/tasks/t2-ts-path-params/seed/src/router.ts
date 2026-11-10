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
    for (const route of this.routes) {
      if (route.method === wanted && route.path === path) {
        return route.handler({});
      }
    }
    return undefined;
  }
}
