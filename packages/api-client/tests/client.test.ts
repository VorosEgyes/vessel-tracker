import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "../src/index.js";

describe("API client", () => {
  it("serializes catalog filters and returns typed data", async () => {
    const fetch = vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      expect(url.pathname).toBe("/api/v1/vessels");
      expect(url.searchParams.get("area")).toBe("duna");
      expect(url.searchParams.get("page")).toBe("2");
      return Response.json({
        data: [],
        meta: { total: 0, page: 2, per_page: 50, has_more: false },
      });
    });
    const client = createApiClient({ baseUrl: "https://example.test", fetch });
    const result = await client.GET("/api/v1/vessels", {
      params: { query: { area: "duna", page: 2 } },
    });
    expect(result.error).toBeUndefined();
    expect(result.data?.meta.has_more).toBe(false);
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("exposes HTTP errors and propagates network failures", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({ detail: "missing" }, { status: 404 }),
      )
      .mockRejectedValueOnce(new Error("network unavailable"));
    const client = createApiClient({ baseUrl: "https://example.test", fetch });
    const missing = await client.GET("/api/v1/ports/{id}", {
      params: { path: { id: 999 } },
    });
    expect(missing.response.status).toBe(404);
    expect(missing.error).toEqual({ detail: "missing" });
    await expect(client.GET("/api/v1/waterways")).rejects.toThrow(
      "network unavailable",
    );
  });
});
