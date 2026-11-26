# TypeScript API-kliens

Az API-típusok a FastAPI OpenAPI-sémájából generálódnak. A kliens az
`openapi-fetch` csomagra épül, böngészőben és szerveroldalon is használható.

```typescript
import { createApiClient } from "@vessel-tracker/api-client";

const client = createApiClient({ baseUrl: "http://localhost:8000" });
const { data, error, response } = await client.GET("/api/v1/vessels", {
  params: { query: { area: "duna", lang: "hu" } },
});
if (error) {
  console.error("API-hiba:", response.status, error);
} else {
  console.log(data.data);
}
```

HTTP-hiba esetén az `error` és a `response` tér vissza; hálózati hiba
esetén a kérés kivételt dob. A `baseUrl`-t a fogyasztó környezete adja meg.

## Fejlesztés

A repó gyökeréből:

```sh
uv sync --extra dev
pnpm install --frozen-lockfile
pnpm api:generate
pnpm api:check
pnpm typecheck
pnpm test
```

Az `api:generate` frissíti a `docs/api/v1/openapi.json` sémát és a
`src/generated.ts` típusokat. Az `api:check` újragenerál, és hibával
leáll, ha bármelyik eltér a kódtól. Adatbázis nem szükséges.
Alapértelmezésben a generátor `uv run python`-t használ; meglévő Python
környezethez az `API_PYTHON` változóban adható meg az interpreter útvonala.
