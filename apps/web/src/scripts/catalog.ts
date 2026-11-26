import {
  fetchCatalog,
  messages,
  parseQuery,
  translatedValue,
  type Area,
  type Catalog,
  type Language,
} from "../lib/catalog";

const root = document.querySelector<HTMLElement>("#catalog");
const form = document.querySelector<HTMLFormElement>("#filters");
const results = document.querySelector<HTMLTableSectionElement>("#results");
const feedback = document.querySelector<HTMLElement>("#feedback");
const empty = document.querySelector<HTMLElement>("#empty");
const previous = document.querySelector<HTMLButtonElement>("#previous");
const next = document.querySelector<HTMLButtonElement>("#next");
const pageLabel = document.querySelector<HTMLElement>("#page-label");

if (
  !root ||
  !form ||
  !results ||
  !feedback ||
  !empty ||
  !previous ||
  !next ||
  !pageLabel
) {
  throw new Error("Catalogue page is missing required elements");
}

const lang = root.dataset.lang as Language;
const area = root.dataset.area as Area;
const t = messages[lang];
const apiBase = root.dataset.apiBase || window.location.origin;
let requestId = 0;

function render(catalog: Catalog) {
  results!.replaceChildren();
  for (const vessel of catalog.data) {
    const row = document.createElement("tr");
    const values = [
      vessel.name,
      vessel.vessel_type_name,
      vessel.identifier ?? t.missing,
      vessel.operator_name ?? t.missing,
      translatedValue(lang, vessel.status),
      translatedValue(lang, vessel.verification_level) +
        (vessel.verification_source === "stored_stale" ? ` · ${t.stale}` : ""),
    ];
    for (const [index, value] of values.entries()) {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (index === 0) cell.className = "vessel-name";
      row.append(cell);
    }
    results!.append(row);
  }
  empty!.hidden = catalog.data.length > 0;
  previous!.disabled = catalog.meta.page <= 1;
  next!.disabled = !catalog.meta.has_more;
  pageLabel!.textContent = `${t.page} ${catalog.meta.page}`;
}

async function load() {
  const current = ++requestId;
  const query = parseQuery(
    new URLSearchParams(window.location.search),
    area,
    lang,
  );
  for (const name of ["q", "sort", "order"] as const) {
    const field = form!.elements.namedItem(name);
    if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement)
      field.value = query[name] ?? "";
  }
  feedback!.hidden = false;
  feedback!.textContent = t.loading;
  previous!.disabled = true;
  next!.disabled = true;
  try {
    const data = await fetchCatalog(
      apiBase,
      area,
      lang,
      new URLSearchParams(window.location.search),
    );
    if (current !== requestId) return;
    render(data);
    feedback!.hidden = true;
  } catch (error) {
    if (current !== requestId) return;
    console.error("Catalogue request failed", error);
    feedback!.textContent = t.error;
    results!.replaceChildren();
    empty!.hidden = true;
  }
}

function navigate(params: URLSearchParams) {
  const query = params.toString();
  history.pushState(
    null,
    "",
    `${window.location.pathname}${query ? `?${query}` : ""}`,
  );
  void load();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const params = new URLSearchParams();
  for (const name of ["q", "sort", "order"]) {
    const value = data.get(name);
    if (typeof value === "string" && value.trim())
      params.set(name, value.trim());
  }
  navigate(params);
});

for (const [button, direction] of [
  [previous, -1],
  [next, 1],
] as const) {
  button.addEventListener("click", () => {
    const params = new URLSearchParams(window.location.search);
    const page = parseQuery(params, area, lang).page ?? 1;
    params.set("page", String(Math.max(1, page + direction)));
    navigate(params);
  });
}
window.addEventListener("popstate", () => void load());
if (window.location.search) void load();
