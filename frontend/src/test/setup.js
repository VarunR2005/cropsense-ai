import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver, which Recharts' responsive charts need.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver || ResizeObserverStub;
