import {
  createApiClient,
  type components,
  type operations,
} from "@vessel-tracker/api-client";

export const languages = ["hu", "en", "de"] as const;
export const areas = ["duna", "balaton"] as const;
export type Language = (typeof languages)[number];
export type Area = (typeof areas)[number];
export type Catalog = components["schemas"]["Page_VesselListItem_"];
type CatalogQuery =
  operations["list_vessels_endpoint_api_v1_vessels_get"]["parameters"]["query"];

export const messages = {
  hu: {
    title: "Hajókatalógus",
    duna: "Duna",
    balaton: "Balaton",
    subtitle: "Fedezd fel a vízi utak hajóit.",
    search: "Keresés hajónévre",
    searchButton: "Keresés",
    sort: "Rendezés",
    name: "Hajónév",
    type: "Típus",
    identifier: "Azonosító",
    operator: "Üzemeltető",
    status: "Állapot",
    verification: "Bizonyosság",
    length: "Hossz",
    updated: "Frissítés",
    order: "Sorrend",
    ascending: "Növekvő",
    descending: "Csökkenő",
    previous: "Előző",
    next: "Következő",
    page: "Oldal",
    empty: "Nincs találat. Próbálj más keresést vagy válts vízterületet.",
    error:
      "A katalógus most nem érhető el. Ellenőrizd a kapcsolatot és próbáld újra.",
    loading: "A katalógus betöltése…",
    missing: "Nincs adat",
    nojs: "A szűréshez és lapozáshoz JavaScript szükséges.",
    active: "Aktív",
    inactive: "Inaktív",
    excluded: "Kizárt",
    scrapped: "Selejtezett",
    ais_identified: "AIS azonosított",
    ais_partial: "AIS részleges",
    operator_claimed: "Üzemeltetői adat",
    name_only: "Csak név",
    unverified: "Nem ellenőrzött",
    stale: "Az eltárolt szint eltér",
  },
  en: {
    title: "Vessel catalogue",
    duna: "Danube",
    balaton: "Lake Balaton",
    subtitle: "Explore vessels on our waterways.",
    search: "Search vessel names",
    searchButton: "Search",
    sort: "Sort by",
    name: "Vessel name",
    type: "Type",
    identifier: "Identifier",
    operator: "Operator",
    status: "Status",
    verification: "Verification",
    length: "Length",
    updated: "Updated",
    order: "Order",
    ascending: "Ascending",
    descending: "Descending",
    previous: "Previous",
    next: "Next",
    page: "Page",
    empty: "No results. Try another search or switch waterways.",
    error: "The catalogue is unavailable. Check your connection and try again.",
    loading: "Loading catalogue…",
    missing: "No data",
    nojs: "JavaScript is required for filtering and pagination.",
    active: "Active",
    inactive: "Inactive",
    excluded: "Excluded",
    scrapped: "Scrapped",
    ais_identified: "AIS identified",
    ais_partial: "Partial AIS",
    operator_claimed: "Operator supplied",
    name_only: "Name only",
    unverified: "Unverified",
    stale: "Stored verification differs",
  },
  de: {
    title: "Schiffskatalog",
    duna: "Donau",
    balaton: "Balaton",
    subtitle: "Entdecken Sie Schiffe auf unseren Gewässern.",
    search: "Schiffsnamen suchen",
    searchButton: "Suchen",
    sort: "Sortieren nach",
    name: "Schiffsname",
    type: "Typ",
    identifier: "Kennung",
    operator: "Betreiber",
    status: "Status",
    verification: "Verifizierung",
    length: "Länge",
    updated: "Aktualisierung",
    order: "Reihenfolge",
    ascending: "Aufsteigend",
    descending: "Absteigend",
    previous: "Zurück",
    next: "Weiter",
    page: "Seite",
    empty: "Keine Treffer. Ändern Sie die Suche oder das Gewässer.",
    error:
      "Der Katalog ist nicht erreichbar. Bitte prüfen Sie die Verbindung und versuchen Sie es erneut.",
    loading: "Katalog wird geladen…",
    missing: "Keine Daten",
    nojs: "Für Filter und Seitenwechsel ist JavaScript erforderlich.",
    active: "Aktiv",
    inactive: "Inaktiv",
    excluded: "Ausgeschlossen",
    scrapped: "Verschrottet",
    ais_identified: "AIS identifiziert",
    ais_partial: "AIS teilweise",
    operator_claimed: "Betreiberangabe",
    name_only: "Nur Name",
    unverified: "Nicht geprüft",
    stale: "Gespeicherte Bewertung abweichend",
  },
} as const;

export function parseQuery(
  params: URLSearchParams,
  area: Area,
  lang: Language,
): CatalogQuery {
  const sort = params.get("sort");
  const order = params.get("order");
  const rawPage = params.get("page") ?? "1";
  const page = /^[1-9]\d*$/.test(rawPage) ? Number(rawPage) : 1;
  return {
    area,
    lang,
    q: params.get("q")?.trim() || undefined,
    sort:
      sort === "type" || sort === "length" || sort === "updated_at"
        ? sort
        : "name",
    order: order === "desc" ? "desc" : "asc",
    page: Number.isSafeInteger(page) ? page : 1,
    per_page: 50,
  };
}

export async function fetchCatalog(
  baseUrl: string,
  area: Area,
  lang: Language,
  params: URLSearchParams,
  fetcher?: typeof fetch,
): Promise<Catalog> {
  const client = createApiClient({
    baseUrl,
    ...(fetcher ? { fetch: fetcher } : {}),
  });
  const result = await client.GET("/api/v1/vessels", {
    params: { query: parseQuery(params, area, lang) },
  });
  if (!result.response.ok || !result.data) {
    throw new Error(`Catalogue request failed: HTTP ${result.response.status}`);
  }
  return result.data;
}

export function translatedValue(lang: Language, value: string): string {
  const labels: Record<string, string> = messages[lang];
  return labels[value] ?? value;
}
