import { describe, expect, it, vi } from "vitest";
import {
  fetchCatalog,
  messages,
  parseQuery,
  translatedValue,
} from "../src/lib/catalog";

describe("catalogue", () => {
  it("validates URL state and preserves the selected area and language", () => {
    expect(
      parseQuery(
        new URLSearchParams("q=%20boat%20&sort=length&order=desc&page=2"),
        "balaton",
        "en",
      ),
    ).toEqual({
      area: "balaton",
      lang: "en",
      q: "boat",
      sort: "length",
      order: "desc",
      page: 2,
      per_page: 50,
    });
    expect(
      parseQuery(
        new URLSearchParams("sort=bad&order=bad&page=-5"),
        "duna",
        "hu",
      ),
    ).toMatchObject({
      sort: "name",
      order: "asc",
      page: 1,
    });
  });

  it("fetches with typed query parameters and propagates HTTP and network errors", async () => {
    const fetcher: typeof fetch = vi.fn(async (request) => {
      expect(
        new URL(
          request instanceof Request ? request.url : String(request),
        ).searchParams.get("area"),
      ).toBe("balaton");
      return Response.json({
        data: [],
        meta: { page: 1, total: 0, per_page: 50, has_more: false },
      });
    });
    const data = await fetchCatalog(
      "https://example.test",
      "balaton",
      "de",
      new URLSearchParams(),
      fetcher,
    );
    expect(data.data).toEqual([]);
    await expect(
      fetchCatalog(
        "https://example.test",
        "duna",
        "hu",
        new URLSearchParams(),
        async () => new Response(null, { status: 503 }),
      ),
    ).rejects.toThrow("HTTP 503");
    await expect(
      fetchCatalog(
        "https://example.test",
        "duna",
        "hu",
        new URLSearchParams(),
        async () => {
          throw new Error("offline");
        },
      ),
    ).rejects.toThrow("offline");
  });

  it("has translated labels for all catalogue languages", () => {
    for (const lang of ["hu", "en", "de"] as const) {
      expect(translatedValue(lang, "active")).toBe(messages[lang].active);
      expect(translatedValue(lang, "unknown")).toBe("unknown");
    }
  });
});
