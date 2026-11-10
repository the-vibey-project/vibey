import assert from "node:assert/strict";
import { test } from "node:test";
import { createApp } from "../src/app.ts";
import { response } from "../src/http.ts";
import type { Handler, Request } from "../src/http.ts";
import { addResponseHeader, compose, requireHeader } from "../src/middleware.ts";
import type { Middleware } from "../src/middleware.ts";

function req(method = "GET", path = "/", headers: Record<string, string> = {}): Request {
  return { method, path, headers };
}

const ok: Handler = () => response(200, "ok");

test("compose with no middleware is the handler", () => {
  assert.deepEqual(compose([], ok)(req()), response(200, "ok"));
});

test("first middleware is outermost", () => {
  const log: string[] = [];
  const tag = (name: string): Middleware => (r, next) => {
    log.push(`${name}:in`);
    const res = next(r);
    log.push(`${name}:out`);
    return res;
  };
  const handler: Handler = () => {
    log.push("handler");
    return response(200, "ok");
  };
  compose([tag("a"), tag("b")], handler)(req());
  assert.deepEqual(log, ["a:in", "b:in", "handler", "b:out", "a:out"]);
});

test("a middleware can short-circuit", () => {
  let reached = false;
  const stop: Middleware = () => response(418, "teapot");
  const handler: Handler = () => {
    reached = true;
    return response(200, "ok");
  };
  assert.equal(compose([stop], handler)(req()).status, 418);
  assert.equal(reached, false);
});

test("requireHeader passes when the header is present, any case", () => {
  const h = compose([requireHeader("X-Token")], ok);
  assert.equal(h(req("GET", "/", { "x-token": "abc" })).status, 200);
  assert.equal(h(req("GET", "/", { "X-TOKEN": "abc" })).status, 200);
});

test("requireHeader rejects a missing header with the given name in the body", () => {
  const h = compose([requireHeader("X-Token")], ok);
  assert.deepEqual(h(req()), response(401, "missing header: X-Token"));
});

test("requireHeader treats an empty value as missing and honours the status", () => {
  const h = compose([requireHeader("Auth", 403)], ok);
  const res = h(req("GET", "/", { auth: "" }));
  assert.equal(res.status, 403);
  assert.equal(res.body, "missing header: Auth");
});

test("requireHeader does not call next when rejecting", () => {
  let called = false;
  const handler: Handler = () => {
    called = true;
    return response(200, "ok");
  };
  compose([requireHeader("a")], handler)(req());
  assert.equal(called, false);
});

test("addResponseHeader adds and replaces headers", () => {
  const handler: Handler = () => response(200, "ok", { a: "1", b: "old" });
  const res = compose([addResponseHeader("b", "new"), addResponseHeader("c", "3")], handler)(req());
  assert.deepEqual(res.headers, { a: "1", b: "new", c: "3" });
});

test("addResponseHeader does not mutate the response it receives", () => {
  const original = response(200, "ok", { a: "1" });
  const res = compose([addResponseHeader("b", "2")], () => original)(req());
  assert.deepEqual(original.headers, { a: "1" });
  assert.notEqual(res, original);
});

test("createApp routes as before", () => {
  const app = createApp({ "GET /hi": () => response(200, "hello") });
  assert.deepEqual(app(req("GET", "/hi")), response(200, "hello"));
  assert.deepEqual(app(req("POST", "/hi")), response(404, "not found"));
  assert.deepEqual(app(req("GET", "/nope")), response(404, "not found"));
});

test("createApp applies middlewares in order around routing", () => {
  const app = createApp({ "GET /hi": () => response(200, "hello") }, [
    requireHeader("x-key"),
    addResponseHeader("x-served", "yes"),
  ]);
  assert.equal(app(req("GET", "/hi")).status, 401);
  const res = app(req("GET", "/hi", { "X-Key": "k" }));
  assert.equal(res.status, 200);
  assert.equal(res.headers["x-served"], "yes");
});

test("middlewares also see the 404", () => {
  const app = createApp({}, [addResponseHeader("x-served", "yes")]);
  const res = app(req("GET", "/missing"));
  assert.equal(res.status, 404);
  assert.equal(res.headers["x-served"], "yes");
});

test("a throwing handler becomes a 500", () => {
  const app = createApp({
    "GET /boom": () => {
      throw new Error("bad");
    },
  });
  assert.deepEqual(app(req("GET", "/boom")), response(500, "internal error"));
});

test("a throwing middleware becomes a 500 without inner or outer headers", () => {
  const boom: Middleware = () => {
    throw new Error("bad");
  };
  const app = createApp({ "GET /x": ok }, [addResponseHeader("x-served", "yes"), boom]);
  assert.deepEqual(app(req("GET", "/x")), response(500, "internal error"));
});
