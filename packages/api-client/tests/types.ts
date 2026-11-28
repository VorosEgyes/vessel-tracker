import type { createApiClient } from "../src/index.js";

declare const client: ReturnType<typeof createApiClient>;

if (false) {
  client.GET("/api/v1/vessels", { params: { query: { area: "duna" } } });
  // @ts-expect-error area is required
  client.GET("/api/v1/vessels", { params: { query: {} } });
  // @ts-expect-error only documented areas are accepted
  client.GET("/api/v1/vessels", { params: { query: { area: "ocean" } } });
  client.GET("/api/v1/ports/{id}", {
    // @ts-expect-error id is numeric
    params: { path: { id: "bad" } },
  });
}
