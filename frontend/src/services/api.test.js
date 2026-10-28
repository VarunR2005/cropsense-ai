import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api.js";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("API error handling", () => {
  it("turns FastAPI validation errors into readable messages", async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ loc: ["body", "email"], msg: "value is not a valid email address" }] }),
    }));
    await expect(api.register({})).rejects.toThrow("email: value is not a valid email address");
  });

  it("shows plain string errors from the backend", async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Weather is not configured." }),
    }));
    await expect(api.weather("Mysuru")).rejects.toMatchObject({ message: "Weather is not configured.", status: 503 });
  });

  it("sends the bearer token when one is stored", async () => {
    localStorage.setItem("cropsense_token", "abc123");
    globalThis.fetch = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ id: 1 }) }));
    await api.me();
    const [, options] = globalThis.fetch.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer abc123");
  });
});
