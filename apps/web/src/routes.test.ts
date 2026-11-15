import { describe, expect, it } from "vitest";
import { viewFromHash } from "./routes";

describe("workbench routes", () => {
  it("accepts the six primary views", () => {
    expect(viewFromHash("#new")).toBe("new");
    expect(viewFromHash("#results")).toBe("results");
    expect(viewFromHash("#related")).toBe("related");
    expect(viewFromHash("#campaign")).toBe("campaign");
    expect(viewFromHash("#details")).toBe("details");
  });

  it("falls back to the dashboard for unknown routes", () => {
    expect(viewFromHash("#unknown")).toBe("dashboard");
    expect(viewFromHash("")).toBe("dashboard");
  });
});