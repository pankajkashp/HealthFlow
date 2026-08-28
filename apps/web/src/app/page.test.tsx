import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HomePage from "./page";

/**
 * Foundation test for the HealthFlow shell page.
 *
 * Verifies that the initial Next.js foundation renders correctly
 * without errors or exceptions.
 *
 * Ref: Phase 1 specification §3 (Frontend foundation) & §10 (Testing foundation).
 */
describe("HomePage", () => {
  it("renders the HealthFlow heading", () => {
    render(<HomePage />);
    const heading = screen.getByRole("heading", { level: 1, name: /HealthFlow/i });
    expect(heading).toBeInTheDocument();
  });

  it("renders the foundation status badge", () => {
    render(<HomePage />);
    const badge = screen.getByText(/^Foundation$/, { selector: "span" });
    expect(badge).toBeInTheDocument();
  });
});
