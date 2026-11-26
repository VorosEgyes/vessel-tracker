import createClient, { type ClientOptions } from "openapi-fetch";
import type { paths } from "./generated.js";

export type { components, operations, paths } from "./generated.js";

export function createApiClient(options: ClientOptions) {
  return createClient<paths>(options);
}
