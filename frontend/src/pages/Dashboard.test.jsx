import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../services/api.js";
import Dashboard from "./Dashboard.jsx";
// Real response shape, generated from the backend's dashboard code
import fixture from "../test/fixtures/dashboard.json";

vi.mock("../services/api.js", () => ({
  api: { dashboard: vi.fn() },
}));

beforeEach(() => {
  api.dashboard.mockResolvedValue(fixture);
});

describe("Dashboard", () => {
  it("shows the real totals and recent predictions from the API", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(await screen.findByText("Yield predictions")).toBeInTheDocument();
    expect(screen.getByText(String(fixture.totals.yield_predictions))).toBeInTheDocument();
    expect(screen.getAllByText("Rice").length).toBeGreaterThan(0);
  });

  it("is honest about features that are not built yet", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(await screen.findByText(fixture.disease_history.note)).toBeInTheDocument();
    expect(screen.getByText(fixture.farms.note)).toBeInTheDocument();
  });

  it("shows an error when the request fails", async () => {
    api.dashboard.mockRejectedValue(Object.assign(new Error("Server exploded"), { status: 500 }));
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(await screen.findByText("Server exploded")).toBeInTheDocument();
  });
});
