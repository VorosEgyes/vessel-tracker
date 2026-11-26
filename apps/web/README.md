# Hajókatalógus frontend

Astro statikus katalógus magyar, angol és német nyelven, külön Duna- és
Balaton-oldalakkal. A kezdő lista buildkor az API-ból készül; a keresés,
a rendezés és a lapozás a böngészőből az élő API-t használja.

```sh
pnpm install --frozen-lockfile
API_BASE_URL=http://localhost:8000 pnpm --filter @vessel-tracker/web dev
API_BASE_URL=http://localhost:8000 pnpm --filter @vessel-tracker/web build
pnpm --filter @vessel-tracker/web preview
```

Az `API_BASE_URL` a build/dev szerver számára elérhető API-cím, megadása
kötelező. A böngésző alapértelmezésben ugyanazon eredeten a `/api/v1`
útvonalat hívja: éles környezetben a reverse proxy irányítsa ezt az API-ra.
Eltérő eredet esetén a buildkor beállított `PUBLIC_API_BASE_URL` szükséges;
az API CORS-beállításában a webes originnek szerepelnie kell. Az API hibája
a buildet megszakítja, a böngészőben pedig hibaüzenetet jelenít meg.

Jelenleg csak a katalóguslista készült el; hajóadatlap, build-hook és
automatikus újraépítés még nincs. JavaScript nélkül a buildkori lista
látható, az interaktív szűrés és lapozás nem működik.
