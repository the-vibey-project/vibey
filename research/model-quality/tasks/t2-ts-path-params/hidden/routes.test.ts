import assert from "node:assert/strict";
import { test } from "node:test";
import { matchPath } from "../src/pattern.ts";
import { Router } from "../src/router.ts";

test("literal patterns match exactly", () => {
  assert.deepEqual(matchPath("/users", "/users"), {});
  assert.equal(matchPath("/users", "/user"), null);
  assert.equal(matchPath("/users", "/Users"), null);
  assert.equal(matchPath("/users/list", "/users"), null);
});

test("root matches root only", () => {
  assert.deepEqual(matchPath("/", "/"), {});
  assert.equal(matchPath("/", "/x"), null);
});

test("a trailing slash is ignored on both sides", () => {
  assert.deepEqual(matchPath("/users", "/users/"), {});
  assert.deepEqual(matchPath("/users/", "/users"), {});
  assert.deepEqual(matchPath("/u/:id/", "/u/5"), { id: "5" });
});

test("named parameters capture one segment", () => {
  assert.deepEqual(matchPath("/users/:id", "/users/42"), { id: "42" });
  assert.deepEqual(matchPath("/a/:x/b/:y", "/a/1/b/2"), { x: "1", y: "2" });
  assert.equal(matchPath("/users/:id", "/users"), null);
  assert.equal(matchPath("/users/:id", "/users/1/extra"), null);
  assert.equal(matchPath("/users/:id", "/users//"), null);
});

test("parameters are percent-decoded", () => {
  assert.deepEqual(matchPath("/f/:name", "/f/a%20b"), { name: "a b" });
  assert.deepEqual(matchPath("/f/:name", "/f/caf%C3%A9"), { name: "café" });
});

test("malformed percent-encoding does not match", () => {
  assert.equal(matchPath("/f/:name", "/f/%E0%A4%A"), null);
  assert.equal(matchPath("/f/:name", "/f/100%"), null);
});

test("a trailing star captures the rest, undecoded", () => {
  assert.deepEqual(matchPath("/files/*", "/files/a/b/c"), { "*": "a/b/c" });
  assert.deepEqual(matchPath("/files/*", "/files/a%20b"), { "*": "a%20b" });
  assert.deepEqual(matchPath("/files/*", "/files/one"), { "*": "one" });
});

test("a star needs at least one segment", () => {
  assert.equal(matchPath("/files/*", "/files"), null);
  assert.equal(matchPath("/files/*", "/files/"), null);
});

test("star combines with parameters", () => {
  assert.deepEqual(matchPath("/u/:id/*", "/u/7/x/y"), { id: "7", "*": "x/y" });
});

test("router passes params to the handler", () => {
  const router = new Router();
  router.add("GET", "/users/:id", (p) => `user ${p["id"]}`);
  assert.equal(router.dispatch("GET", "/users/9"), "user 9");
  assert.equal(router.dispatch("get", "/users/10/"), "user 10");
});

test("exact routes win over earlier pattern routes", () => {
  const router = new Router();
  router.add("GET", "/users/:id", () => "pattern");
  router.add("GET", "/users/me", () => "exact");
  assert.equal(router.dispatch("GET", "/users/me"), "exact");
  assert.equal(router.dispatch("GET", "/users/you"), "pattern");
});

test("among pattern routes the first registered wins", () => {
  const router = new Router();
  router.add("GET", "/a/:x", () => "first");
  router.add("GET", "/a/*", () => "second");
  assert.equal(router.dispatch("GET", "/a/1"), "first");
  assert.equal(router.dispatch("GET", "/a/1/2"), "second");
});

test("routes only match their own method", () => {
  const router = new Router();
  router.add("post", "/items/:id", () => "posted");
  assert.equal(router.dispatch("GET", "/items/1"), undefined);
  assert.equal(router.dispatch("POST", "/items/1"), "posted");
});

test("exact handlers receive empty params and unmatched paths give undefined", () => {
  const router = new Router();
  router.add("GET", "/ping", (p) => `pong ${Object.keys(p).length}`);
  assert.equal(router.dispatch("GET", "/ping"), "pong 0");
  assert.equal(router.dispatch("GET", "/nope"), undefined);
});

test("a malformed escape falls through to later routes", () => {
  const router = new Router();
  router.add("GET", "/f/:name", () => "param");
  router.add("GET", "/f/*", () => "star");
  assert.equal(router.dispatch("GET", "/f/%E0%A4%A"), "star");
});
