import { execFile } from "node:child_process";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { promisify } from "node:util";
import { afterAll, beforeAll, expect, it } from "vitest";

const exec = promisify(execFile);
const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://localhost");
  const area = url.searchParams.get("area");
  response.writeHead(200, { "Content-Type": "application/json" });
  response.end(
    JSON.stringify({
      data: [
        {
          id: 1,
          slug: "test",
          name: `${area} test vessel`,
          vessel_type_name: "Ship",
          identifier: null,
          operator_name: null,
          operating_area: area,
          status: "active",
          verification_level: "name_only",
          verification_source: "computed",
        },
      ],
      meta: { total: 1, page: 1, per_page: 50, has_more: false },
    }),
  );
});
let apiBase = "";

beforeAll(async () => {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string")
    throw new Error("Missing test API port");
  apiBase = `http://127.0.0.1:${address.port}`;
});

afterAll(async () => {
  await new Promise<void>((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
});

it("builds six localized pages with API data and fails when the API is unavailable", async () => {
  const env = {
    ...process.env,
    API_BASE_URL: apiBase,
    ASTRO_TELEMETRY_DISABLED: "1",
  };
  await exec("./node_modules/.bin/astro", ["build"], { env });
  for (const language of ["hu", "en", "de"]) {
    for (const area of ["duna", "balaton"]) {
      const html = await readFile(
        `dist/${language}/${area}/hajok/index.html`,
        "utf8",
      );
      expect(html).toContain(`${area} test vessel`);
      expect(html).toContain(`<html lang="${language}">`);
    }
  }
  await expect(
    exec("./node_modules/.bin/astro", ["build"], {
      env: { ...env, API_BASE_URL: "http://127.0.0.1:1" },
    }),
  ).rejects.toThrow();
}, 60_000);
