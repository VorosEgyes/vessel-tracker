-- A vessel-tracker sémája — GENERÁLT FÁJL, NE MODDÍTSD KÉZZEL!
--
-- A forrás: docs/megvalosulas/megvalosulas-02-adatbazis-ddl.md
--            (a 02-es DDL-terv SQL-blokkjaival)
-- A generátor: db/tools/gen_ddl.py
-- A CI-ellenőrzés: a `just ddl-diff` (a 07 §8.1 10b. lépése)
--
-- **A terv módosításakor a `just ddl-generate` futtatása kötelező**,
-- különben a `git diff --exit-code` elbukik a CI-ban.

-- a táblák: 71 | az indexek: 63

CREATE TABLE language (
    code        char(2) PRIMARY KEY,          -- 'hu', 'de', 'en'
    name_native text NOT NULL,
    name_en     text NOT NULL,
    is_rtl      boolean NOT NULL DEFAULT false
);
;
-- A forrás-nyilvántartás: a legkorábbi tabla, mert
-- sok mas tabla source_id-je erre mutat (FK-ordering)
CREATE TABLE data_source (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code           text NOT NULL UNIQUE,       -- 'own-ais-budapest', 'spi'
    name           text NOT NULL,
    provider       text,
    license_type   text NOT NULL DEFAULT 'unknown'
                   CHECK (license_type IN
                     ('public','own','contractual','unknown')),
    license_ref    text,                       -- a szerződés vagy a licenc hivatkozása
    coverage_desc  text,
    quality_tier   text NOT NULL DEFAULT 'c'
                   CHECK (quality_tier IN ('a','b','c')),
    is_primary     boolean NOT NULL DEFAULT false,
    active         boolean NOT NULL DEFAULT true
);

-- A nyelvfüggetlen tartalmi kulcs (pl. 'map.legend.locks').
-- **A `name_key` FK-k miatt ez a tabla KORAN jön** — a `basin`,
-- a `notice_type`, az `event_type` és az `article_category` erre
-- mutat (M-3).
CREATE TABLE content_key (
    key             text PRIMARY KEY,
    domain          text NOT NULL,         -- 'ui' | 'vessel' | 'port' | 'article'
    description     text,
    source_lang     char(2) NOT NULL REFERENCES language(code),
    is_placeholder  boolean NOT NULL DEFAULT false
);
CREATE INDEX content_key_domain_idx ON content_key (domain);
;
CREATE TABLE app_user (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         text UNIQUE,
    display_name  text,
    locale        char(2) NOT NULL DEFAULT 'hu' REFERENCES language(code),
    unit_system   text NOT NULL DEFAULT 'metric'
                  CHECK (unit_system IN ('metric','imperial','nautical')),
    -- A 'system' provider a **hatterben futo szolgaltatasfiók**
    -- (a dedikalt 'system' aktor az audit-hoz, a cron jobok) —
    -- ezeknek nincs jelszavuk, ezert a `password_hash` CHECK
    -- nem vonatkozik ra (P1-14).
    auth_provider text NOT NULL DEFAULT 'local'
                  CHECK (auth_provider IN ('local','oidc','system')),
    auth_subject  text,
    -- **V-N-7: a `role` oszlopot a szerkeszto NEM valtozthatja** —
    -- kulonben magat adminna emelhetne. A DB-szintu vedelem: a
    -- trigger a `role` oszlop változásat csak a `admin` szerep
    -- számára engedi.
    role          text NOT NULL DEFAULT 'editor'
                  CHECK (role IN ('editor','admin')),
    password_hash text,               -- Argon2id; a 'local' providerhez
    session_token_hash text UNIQUE,   -- a session cookie SHA-256-ja
    session_expires_at timestamptz,
    status        text NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','disabled')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz,
    last_login_at timestamptz,
    UNIQUE (auth_provider, auth_subject),
    -- A 'local' providerhez a jelszó-hash KOTELEZO (P1-14): kulonben
    -- egy hash nelkuli 'local' felhasznalo be lehet jelentkezni?
    -- nem — de a belepites utan nem tud jelszot valtani, es a
    -- hiba a belepiteskor nem derul ki.
    CHECK (auth_provider <> 'local' OR password_hash IS NOT NULL)
);
;
CREATE TABLE country (
    code       char(2) PRIMARY KEY,          -- ISO 3166-1 alpha-2
    name_local text NOT NULL,
    eu_member  boolean NOT NULL DEFAULT false
);

CREATE TABLE waterway (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         text NOT NULL UNIQUE,        -- 'Duna', 'Sava', 'RMD'
    waterway_type text NOT NULL
                 CHECK (waterway_type IN ('main','tributary','canal','lake')),
    length_km    numeric(8,2),
    is_active    boolean NOT NULL DEFAULT true
);

CREATE TABLE waterway_i18n (
    waterway_id bigint NOT NULL REFERENCES waterway(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    name        text NOT NULL,
    description text,
    PRIMARY KEY (waterway_id, lang)
);

-- A folyószakasz: km-tartomány + kockázati szint
CREATE TABLE river_section (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    waterway_id  bigint NOT NULL REFERENCES waterway(id),
    code         text NOT NULL UNIQUE,
    km_from      numeric(8,3) NOT NULL,        -- a Duna km-skálája: Sulina = 0
    km_to        numeric(8,3) NOT NULL,
    country_code char(2) NOT NULL REFERENCES country(code),
    risk_level   text NOT NULL DEFAULT 'low'
                  CHECK (risk_level IN ('low','medium','high')),
    max_draft_m  numeric(4,2),
    fairway_code text,                          -- 2019/1744/EU fairway section code
    CHECK (km_to > km_from)
);

CREATE INDEX river_section_waterway_km_idx
    ON river_section (waterway_id, km_from, km_to);
CREATE INDEX river_section_country_idx ON river_section (country_code);

-- A folyoszakasz neve fordul (C-3): a F-DET-06 szoveges helye
-- ("Szob-Budapest szakasz") innen jon.
CREATE TABLE river_section_i18n (
    river_section_id bigint NOT NULL REFERENCES river_section(id) ON DELETE CASCADE,
    lang            char(2) NOT NULL REFERENCES language(code),
    name            text NOT NULL,
    description     text,
    PRIMARY KEY (river_section_id, lang)
);
;
CREATE TABLE waterway_corridor (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    waterway_id bigint NOT NULL REFERENCES waterway(id) ON DELETE CASCADE,
    code        text NOT NULL UNIQUE,
    geom        geometry(MultiPolygon,4326) NOT NULL,   -- a folyó korridorja
    buffer_m    numeric(6,1) NOT NULL DEFAULT 500,       -- a középvonalból számított szélesség
    source_id   bigint REFERENCES data_source(id),
    is_active   boolean NOT NULL DEFAULT true
);
CREATE INDEX waterway_corridor_geom_gix ON waterway_corridor USING GIST (geom);
;
CREATE TABLE gauge (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         text NOT NULL UNIQUE,
    waterway_id  bigint NOT NULL REFERENCES waterway(id),
    river_km     numeric(8,3) NOT NULL,
    country_code char(2) NOT NULL REFERENCES country(code),
    -- A nulla-pont: MINDIG meg kell adni (H-8), mert a szint
    -- enelkul nem ertelmezheto (abszolut vagy a nullapont felett).
    datum_type   text NOT NULL DEFAULT 'zero_datum'
                 CHECK (datum_type IN ('zero_datum','actl','normal')),
    datum        text NOT NULL,                  -- a nulla-pont leirasa
    datum_value_cm numeric(8,2),                -- a nullapont erteke cm-ben
    geom         geometry(Point,4326)
);
CREATE INDEX gauge_geom_gix ON gauge USING GIST (geom);

-- A merestallomas neve a fordithato *-i18n tablaban van (C-3):
-- a `code` a kod, a nev fordul.
CREATE TABLE gauge_i18n (
    gauge_id    bigint NOT NULL REFERENCES gauge(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    name        text NOT NULL,
    description text,
    PRIMARY KEY (gauge_id, lang)
);
;
CREATE TABLE port (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         text NOT NULL UNIQUE,          -- 'PT-0147'
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    unlocode     char(5) UNIQUE,                -- UN/LOCODE, nullable
    port_type    text NOT NULL
                 CHECK (port_type IN
                   ('public_port','terminal','lock','anchorage',
                    'shipyard','fuel','bunkering','marina')),
    waterway_id  bigint NOT NULL REFERENCES waterway(id),
    country_code char(2) NOT NULL REFERENCES country(code),
    river_km     numeric(8,3),
    geom         geometry(Point,4326),
    is_active    boolean NOT NULL DEFAULT true,
    CHECK (unlocode IS NULL OR unlocode ~ '^[A-Z]{2}[A-Z0-9]{3}$')
);
CREATE INDEX port_geom_gix ON port USING GIST (geom);
CREATE INDEX port_waterway_km_idx ON port (waterway_id, river_km);
CREATE INDEX port_type_idx ON port (port_type) WHERE is_active;

CREATE TABLE port_i18n (
    port_id    bigint NOT NULL REFERENCES port(id) ON DELETE CASCADE,
    lang       char(2) NOT NULL REFERENCES language(code),
    name       text NOT NULL,
    address    text,
    description text,
    PRIMARY KEY (port_id, lang)
);
-- A F-CAT-09 a kikötőnév keresését is kéri (a UN/LOCODE mellett)
CREATE INDEX port_i18n_name_trgm ON port_i18n
    USING GIN (lower(unaccent(name)) gin_trgm_ops);

CREATE TABLE operator (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    legal_name   text NOT NULL,
    country_code char(2) NOT NULL REFERENCES country(code),
    website      text,
    founded      smallint
);
CREATE INDEX operator_legal_name_trgm ON operator
    USING GIN (lower(unaccent(legal_name)) gin_trgm_ops);

CREATE TABLE operator_i18n (
    operator_id bigint NOT NULL REFERENCES operator(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    display_name text,
    description text,
    PRIMARY KEY (operator_id, lang)
);

CREATE TABLE berth (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    port_id       bigint NOT NULL REFERENCES port(id) ON DELETE CASCADE,
    code          text NOT NULL,
    length_m      numeric(6,2),
    depth_m       numeric(5,2),
    max_draft_m   numeric(4,2),
    unload_rate_t_h numeric(8,2),
    UNIQUE (port_id, code)
);

CREATE TABLE terminal (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    port_id             bigint NOT NULL REFERENCES port(id) ON DELETE CASCADE,
    operator_id         bigint REFERENCES operator(id),
    annual_capacity_t   numeric(12,2),
    storage_capacity_t  numeric(12,2),
    rail_access         boolean NOT NULL DEFAULT false,
    gear_types          text[]
);

CREATE TABLE lock (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    port_id            bigint NOT NULL REFERENCES port(id) ON DELETE CASCADE,
    code               text NOT NULL UNIQUE,
    chamber_count      smallint,
    chamber_length_m   numeric(6,2),
    chamber_width_m    numeric(6,2),
    max_draft_m        numeric(4,2),
    operator_id        bigint REFERENCES operator(id),
    avg_transit_min    smallint,
    river_km           numeric(8,3),
    geom               geometry(Point,4326)
);
CREATE INDEX lock_geom_gix ON lock USING GIST (geom);

-- A zsilip neve fordul (C-3): a Gabcikovo, Zezelj, Iron Gate
-- a katalogus "legyogu valaszai".
CREATE TABLE lock_i18n (
    lock_id     bigint NOT NULL REFERENCES lock(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    name        text NOT NULL,
    description text,
    PRIMARY KEY (lock_id, lang)
);
;
-- A hajótípus: a README szerint a 'code' a PK (nem az 'id')
CREATE TABLE vessel_type (
    code              text PRIMARY KEY,      -- 'INLAND_CARGO_TANKER'
    un_code_28        text,                  -- UN/CEFACT kód
    ais_type_code     smallint,              -- az AIS típuskód
    cargo_category    text,
    is_self_propelled boolean NOT NULL DEFAULT true,
    operating_area    text NOT NULL DEFAULT 'duna'
                      CHECK (operating_area IN ('duna','balaton'))
);

CREATE TABLE vessel_type_i18n (
    vessel_type_code text NOT NULL REFERENCES vessel_type(code) ON DELETE CASCADE,
    lang             char(2) NOT NULL REFERENCES language(code),
    name             text NOT NULL,
    description      text,
    PRIMARY KEY (vessel_type_code, lang)
);


--
-- A `ais_type_code` a **nemzetközi AIS típuskód** (a SOLAS 1–99 és a
-- belvízi UNECE-ERI 8000–8519). A mérés (2026-11-22, a bud01 vevő)
-- **15-féle** kódot mutatott:
--
--   8444 (15 hajó)  8443 (14)  8440 (11)  8000 (8)  60 (8)  69 (7)
--   80 (3)  8450 (3)  0 (1)  90 (1)  51 (2)  8430 (1)  8460 (1)
--   8220 (1)  + 2 null
--
-- **A 8xxx-as sorozat a belvízi (ERI) kódrendszer** — a UNECE
-- SC.3/WP.3 egyezmény és a CESNI ITU-R M.1371 kiegészítése; az
-- 1–99-es a SOLAS (nemzetközi) kódok.
--
-- A `code` a belső kulcs (a `vessel.vessel_type_code` FK-ja mutat
-- erre); az `ais_type_code` az AIS-ből érkező nyers szám.
--
-- A magyar nevek a `vessel_type_i18n` táblába mennek (a `lang='hu'`),
-- a `description` az ERI-eredeti angol nevet tartalmazza.
--
-- FORRÁS: ECE/TRANS/SC.3/WP.3/2020/22 (az UN–IMO hajótípus-
-- megfeleltetés) + a CESNI L_dir_syst_auto_ident_en_1.pdf.



-- Az útvonalak (R1 a 01-es terv §8.1 szerint)
CREATE TABLE route (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                text NOT NULL UNIQUE,          -- 'RTM-BUD'
    origin_port_id      bigint NOT NULL REFERENCES port(id),
    dest_port_id        bigint NOT NULL REFERENCES port(id),
    distance_km         numeric(8,2),
    typical_duration_h  numeric(6,2),
    -- A rakomanytípusok a `cargo_type.code` ertekei (P1-17: a szabad
    -- szoveges tomb helyett ellenorizott lista).
    --
    -- **A CHECK constraint NEM hasznalhat subquery-t** (a PostgreSQL
    -- ezt nem engedi) -> a validalast a `validate_route_cargo_types`
    -- trigger vegezi (a trigger resze §8.1c).
    cargo_types         text[]
);
CREATE INDEX route_origin_idx ON route (origin_port_id);
CREATE INDEX route_dest_idx ON route (dest_port_id);

CREATE TABLE route_stop (
    route_id         bigint NOT NULL REFERENCES route(id) ON DELETE CASCADE,
    seq              smallint NOT NULL,
    port_id          bigint NOT NULL REFERENCES port(id),
    typical_offset_h numeric(6,2),
    PRIMARY KEY (route_id, seq)
);

CREATE TABLE route_i18n (
    route_id    bigint NOT NULL REFERENCES route(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    name        text NOT NULL,
    description text,
    PRIMARY KEY (route_id, lang)
);

-- A rakománytípus (a README szerint a 'code' a PK)
CREATE TABLE cargo_type (
    code          text PRIMARY KEY,
    nst_code      text,
    adn_code      text,
    imdg_code     text,
    is_bulk       boolean NOT NULL DEFAULT false,
    is_container  boolean NOT NULL DEFAULT false
);

CREATE TABLE cargo_type_i18n (
    cargo_type_code text NOT NULL REFERENCES cargo_type(code) ON DELETE CASCADE,
    lang            char(2) NOT NULL REFERENCES language(code),
    name            text NOT NULL,
    description     text,
    PRIMARY KEY (cargo_type_code, lang)
);

CREATE TABLE basin (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    waterway_id  bigint NOT NULL REFERENCES waterway(id) ON DELETE CASCADE,
    code         text NOT NULL UNIQUE,          -- 'nyugati', 'kozepso', 'keleti'
    name_key     text NOT NULL REFERENCES content_key(key),  -- i18n kulcs
    geo_extent   geometry(Polygon,4326),
    UNIQUE (waterway_id, code)
);

CREATE TABLE basin_i18n (
    basin_id bigint NOT NULL REFERENCES basin(id) ON DELETE CASCADE,
    lang     char(2) NOT NULL REFERENCES language(code),
    name     text NOT NULL,
    PRIMARY KEY (basin_id, lang)
);

CREATE TABLE marina (
    id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    port_id               bigint NOT NULL REFERENCES port(id) ON DELETE CASCADE,
    operator_id           bigint REFERENCES operator(id),
    anchoring_allowed     boolean NOT NULL DEFAULT false,
    protected_shore       boolean NOT NULL DEFAULT false,
    berth_count           smallint,
    notice_ref            bigint,               -- a kikötőrend hivatkozása
    UNIQUE (port_id)
);
-- A `notice_ref` FK-ja a `notice` táblához — a `notice` a
-- `0009_content_tables.sql`-ban jon, ezert a constraint is ott
-- all (a `ALTER TABLE ... ADD CONSTRAINT` a `0009` vegein).
;
CREATE TABLE vessel (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- Az MMSI a kulcs (AIS-ből mindig jön), az ENI enrichment
    -- Az azonositok NULL-elhetoek (a Balatoni hajoknak nincs ENI),
    -- ezert NEM `UNIQUE` constraint, hanem partial unique index
    -- (lásd §5.2) — a `UNIQUE` a NULL-okon nem mukodne.
    mmsi                    integer,
    eni                     char(8),
    imo                     char(7),
    callsign                text,
    -- A URL-bari azonosito (F-CAT-07: /{lang}/hajos/{slug}).
    -- A nevbol generalodik, nem tobbpeletes unikalitassal: a
    -- "TESZTHAJO" es a "TESZTHÁJÓ" ugyanaz a hajo, ezert a slug
    -- a nev normalizalt (ascii, kis-nagybetu-ekeze-elhagyo) alakja.
    slug                    text NOT NULL UNIQUE,
    -- A rendezesi nevet denormalizalva (H-4): a hajonev NEM fordul
    -- (a 01-es terv §5.8.4), ezért a latin hivatalos nevet itt is
    -- taroljuk, hogy a kataloguslista ne JOIN-oljon a vessel_i18n-re.
    sort_name               text NOT NULL DEFAULT '',
    vessel_type_code        text NOT NULL REFERENCES vessel_type(code),
    operating_area          text NOT NULL DEFAULT 'duna'
                            CHECK (operating_area IN ('duna','balaton')),
    flag_country_code       char(2) NOT NULL REFERENCES country(code),
    operator_id             bigint REFERENCES operator(id),
    home_port_id            bigint REFERENCES port(id),
    -- A CELALLOMAS (a bori reviewer B-C-3 findingje — a blackboard
    -- szerint a 02 v1.6 es a 03 v0.4 feladata):
    -- a funkcioleiras US-04-je ("a folyamatban levo utjat es varhato
    -- erkezeset akarom latni") a CELALLOMAS az egyik fo kerdes.
    -- A meresben 100%-ban URES (a 04 v1.0 szerint a FI 10-bol jonne,
    -- de a magyar szakaszon a fairway-mezo ures) → **a keszitok adja
    -- meg kezzel** (a 06 §4.2).
    destination             text,
    -- A CELALLOMAS KIKOTOJE (a F-CNT-07 szerint: "a kikotoadatlap
    -- megmutatja, mely hajok erintik" — a funkcioleiras 6.1 szerint
    -- az "erintett kikotok" forrasa az "AIS - cel UN/LOCODE")
    -- -> a hajo celallomasanak UN/LOCODE-ja a `port` tabla egy sora
    destination_port_id     bigint REFERENCES port(id),
    -- A VARHATO ERKEZES (a FI 10 `eta` mezeje — a 04 v1.0 §4.5)
    destination_eta         timestamptz,
    build_year              smallint,
    length_m                numeric(6,2),
    beam_m                  numeric(5,2),
    draught_max_m           numeric(4,2),
    draught_reference       text,        -- mire vonatkozik a merülés
                            -- 'RNW' (a Duna szabályos alacsony vízállása),
                            -- 'lake_operator' (a Balaton: az üzemeltető adata),
                            -- 'unknown' (a forras nem ad meg referenciat)
    draught_reference_text  text,       -- a referencia szovegesen (a UI-hoz)
    gross_tonnage           numeric(10,2),
    deadweight_t            numeric(10,2),
    teu                     integer,
    power_kw                integer,
    ais_class               char(1) CHECK (ais_class IN ('A','B','C')),
    status                  text NOT NULL DEFAULT 'active'
                            CHECK (status IN
                              ('active','excluded','inactive','scrapped')),
    -- A bizonyossági badge (F-DET-14, F-CAT-14). **A F-NF-12
    -- "jogi: minden adathoz a forrás" miatt ez NEM szabadon
    -- beirható ertek legyen** (H-10) — a `vessel_verification`
    -- nezet SZAMOLJA ki a `vessel_identifier` es a
    -- `vessel_data_origin` alapjan. A DB-szintu CHECK a gyakorlatban
    -- nem tamogathato (cross-table), ezert a nezeten keresztul
    -- ellenorizhető (a CI egy minta-adat ellenoriz).
    verification_level      text NOT NULL DEFAULT 'name_only'
                            CHECK (verification_level IN
                              ('ais_identified','ais_partial',
                               'operator_claimed','name_only',
                               'unverified')),
    is_passenger_certified  boolean NOT NULL DEFAULT false,
    passenger_capacity      integer,
    source_id               bigint REFERENCES data_source(id),
    valid_from              date,
    valid_to                date,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now(),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    -- A F-NF-20 a Dunara vonatkozik (RNW); a Balatoni hajonak nincs
    -- RNW-je, ezert a 'lake_operator' es az 'unknown' is ertekes
    -- (H-8) — a UI a `draught_reference_text`-bol olvassa a jelolest.
    CHECK (draught_reference IS NULL OR draught_reference IN
           ('RNW','lake_operator','unknown'))
);
;
CREATE UNIQUE INDEX vessel_mmsi_uniq ON vessel (mmsi) WHERE mmsi IS NOT NULL;
CREATE UNIQUE INDEX vessel_eni_uniq  ON vessel (eni)  WHERE eni  IS NOT NULL;
CREATE UNIQUE INDEX vessel_imo_uniq  ON vessel (imo)  WHERE imo  IS NOT NULL;

-- **A katalóguslista indexei** (H-4: a F-CAT-02 rendezhető lista,
-- a F-CAT-08 szűrők, a F-CAT-14 a bizonyossági szint). A tipikus
-- R1-es lekérdezés:
--   WHERE operating_area='duna' AND status='active'
--   ORDER BY <név> LIMIT 50 OFFSET n
CREATE INDEX vessel_area_status_verification_idx
    ON vessel (operating_area, status, verification_level);
CREATE INDEX vessel_area_operator_idx
    ON vessel (operating_area, operator_id);
CREATE INDEX vessel_area_type_idx
    ON vessel (operating_area, vessel_type_code);

-- **A rendezés indexe** (a `preshaz` reviewer H-4 findingje után):
-- a F-CAT-02 szerint az alapertelmezett rendezes a hajonev szerinti
-- abc — a `vessel.sort_name` oszlopon (a hajonev NEM fordul, ezert
-- denormalizalva). **Ennelkul a rendezes filesort**, minden lapozott
-- keresre.
CREATE INDEX vessel_area_sort_name_idx
    ON vessel (operating_area, sort_name);

-- A mas rendezesek (a `sort=length|updated_at|operator|type`) —
-- a F-CAT-02 szerint a hajonev az alapertelmezett, ezek S-os
-- prioritásuak.
CREATE INDEX vessel_area_length_idx
    ON vessel (operating_area, length_m) WHERE length_m IS NOT NULL;
CREATE INDEX vessel_area_updated_idx
    ON vessel (operating_area, updated_at DESC);
;
CREATE TABLE vessel_i18n (
    vessel_id   bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    name        text NOT NULL,      -- a hivatalos latin név (nem fordul, §5.8.4)
    description text,               -- ez fordul
    PRIMARY KEY (vessel_id, lang)
);
-- **H-6: a F-SRCH-03 szerint a kereses ekezet- es kis-nagybetu-
-- fuggetlen.** A pg_trgm trigram operatorok alaperttelmezetten
-- ERZEKET-ERZEKENYEK, ezért a `unaccent` + `lower()` kifejezes-index
-- kell — es a LEKERDEZES oldalan is ugyanez a kifejezes (külonben az
-- index nem hasznalodik). A 03-as API-terv ezt orokli.
CREATE INDEX vessel_i18n_name_trgm ON vessel_i18n
    USING GIN (lower(unaccent(name)) gin_trgm_ops);

-- **A rendezés** (H-4): a katalóguslista a névre rendez (a F-CAT-02
-- alapértelmezés: hajónév szerinti ábécé). A `vessel_i18n` PK-ja
-- `(vessel_id, lang)` — ez NEM szolgálja a rendezést, kell egy
-- `(lang, name, vessel_id)` index.
CREATE INDEX vessel_i18n_lang_name_idx
    ON vessel_i18n (lang, name, vessel_id);

CREATE TABLE vessel_alias (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id  bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    name       text NOT NULL,
    name_type  text NOT NULL CHECK (name_type IN ('former','official','shipyard')),
    valid_from date,
    valid_to   date
);
CREATE INDEX vessel_alias_name_trgm ON vessel_alias
    USING GIN (lower(unaccent(name)) gin_trgm_ops);

-- A területenként eltérő azonosítók (README 2.10 b)
CREATE TABLE vessel_identifier (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id    bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    identifier_type text NOT NULL
                 CHECK (identifier_type IN
                   ('eni','imo','mmsi','callsign','national_reg_no','internal_code')),
    value        text NOT NULL,
    -- **A KITOLTO ERTEK TILOS** (a 04 §4.4a — a MarineTraffic
    -- support-dokumentacioja a CESNI Inland AIS iranyelv alapjan):
    -- a kényelmes hajoknál az ENI helyett `00000000` jon. Ha ez
    -- bekerülne, (a) a keresö 8 nullas ENI-t talalna, (b) a
    -- `vessel_identifier_active_uniq` unikus indexen minden ilyen
    -- hajo ütközne -> **a minta import elbukna**.
    -- A parser a kitolto erteket `NULL`-ra csereli (nem hajthatja be).
    CONSTRAINT vessel_identifier_value_check
        CHECK (value <> '00000000'),
    is_primary   boolean NOT NULL DEFAULT false,
    origin       text NOT NULL
                 CHECK (origin IN ('ais','official','operator_claimed')),
    valid_from   date,
    valid_to     date,
    source_id    bigint REFERENCES data_source(id)
);
CREATE INDEX vessel_identifier_vessel_idx ON vessel_identifier (vessel_id);
CREATE INDEX vessel_identifier_value_trgm ON vessel_identifier
    USING GIN (lower(unaccent(value)) gin_trgm_ops);

-- **M-4: az egyediség IDŐBELI.** A `UNIQUE (identifier_type, value)`
-- a TORTENETI sorokat is betiltana — egy elront ENI javitasa lehetetlen
-- lenne (a regi sor lezarasa utan sem lehetne ugyanaz az ertek).
-- Az egyediseg csak az AKTIV (valid_to IS NULL) ertekekre vonatkozik.
CREATE UNIQUE INDEX vessel_identifier_active_uniq
    ON vessel_identifier (identifier_type, value) WHERE valid_to IS NULL;

-- "Egy tipusra egy aktiv ertek" (a README 3.3/B)
CREATE UNIQUE INDEX vessel_identifier_primary_uniq
    ON vessel_identifier (vessel_id, identifier_type)
    WHERE is_primary AND valid_to IS NULL;

-- Mezőnkénti eredet (F-DET-15, R1 DoD)
CREATE TABLE vessel_data_origin (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id      bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    field_name     text NOT NULL,      -- 'length_m', 'operator_id', …
    origin         text NOT NULL
                   CHECK (origin IN ('ais','operator_claimed','official','editorial')),
    value_snapshot text,
    source_id      bigint REFERENCES data_source(id),
    observed_at    timestamptz NOT NULL DEFAULT now(),
    confidence     numeric(3,2) CHECK (confidence BETWEEN 0 AND 1),
    is_current     boolean NOT NULL DEFAULT true
);
CREATE INDEX vessel_data_origin_vessel_field_idx
    ON vessel_data_origin (vessel_id, field_name, observed_at DESC);

-- **A konfliktus TÁROLHATÓ** (a README 3.3/B: "Egy mezőnek több
-- eredete lehet (AIS + üzemeltetői állítás); a konfliktus a felületen
-- látható"). Az egyediség a FORRÁSRA vonatkozik, nem az értékre:
-- egy mezőnél egy forrás csak egyszer lehet aktív.
CREATE UNIQUE INDEX vessel_data_origin_active_uniq
    ON vessel_data_origin (vessel_id, field_name, origin)
    WHERE is_current;

-- Az "aktuális érték" nézete: a legfrissebb, legbizalmasabb eredet.
CREATE VIEW vessel_data_origin_current AS
SELECT DISTINCT ON (vessel_id, field_name)
       vessel_id, field_name, origin, value_snapshot,
       source_id, observed_at, confidence
FROM vessel_data_origin
WHERE is_current
ORDER BY vessel_id, field_name, confidence DESC NULLS LAST, observed_at DESC;

-- A KONFLIKTUS nézete: azok a mezők, ahol egynél több forrás van
CREATE VIEW vessel_data_origin_conflicts AS
SELECT vessel_id, field_name, count(*) AS origin_count,
       array_agg(DISTINCT origin) AS origins
FROM vessel_data_origin
WHERE is_current
GROUP BY vessel_id, field_name
HAVING count(*) > 1;

-- A **tulajdonosvaltasok** (H-7: a F-DET-05 "hajotortenet blokk"
-- a tulajdonosvaltasokat is keri, datumtartomannyal).
-- A `vessel.operator_id` az AKTUALIS ertek (gyors olvasas),
-- ez a tabla a PREDMENET.
CREATE TABLE vessel_ownership (
    vessel_id   bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    operator_id bigint NOT NULL REFERENCES operator(id),
    valid_from  date NOT NULL,
    valid_to    date,
    source_id   bigint REFERENCES data_source(id),
    PRIMARY KEY (vessel_id, valid_from),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX vessel_ownership_operator_idx ON vessel_ownership (operator_id);

CREATE TABLE vessel_cert (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id   bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    cert_type   text NOT NULL,
    authority   text,
    issued_at   date,
    expires_at  date,
    document_ref text
);
CREATE INDEX vessel_cert_vessel_idx ON vessel_cert (vessel_id);
CREATE INDEX vessel_cert_expiry_idx ON vessel_cert (expires_at)
    WHERE expires_at IS NOT NULL;

-- A Balatoni szezon (R1-ben a Balaton-katalógushoz kell)
CREATE TABLE vessel_service_period (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id      bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    season_start   date,
    season_end     date,
    service_status text NOT NULL DEFAULT 'year_round'
                   CHECK (service_status IN ('seasonal','year_round','suspended')),
    source_id      bigint REFERENCES data_source(id)
);
CREATE INDEX vessel_service_period_vessel_idx ON vessel_service_period (vessel_id);
;
CREATE TABLE convoy (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lead_vessel_id bigint NOT NULL REFERENCES vessel(id),
    convoy_type   text,
    formed_at     timestamptz,
    dissolved_at  timestamptz,
    status        text NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','dissolved')),
    -- Az R1-ben nincs voyage_id (az a voyage R2, §7)
    CHECK (dissolved_at IS NULL OR formed_at IS NULL OR dissolved_at >= formed_at),
    -- A statusz es az idok osszhangja (P1-19): a 'dissolved' konvojnak
    -- kell egy dissolved_at, az 'active'-nak nem lehet.
    CHECK ((status = 'dissolved' AND dissolved_at IS NOT NULL)
           OR (status = 'active' AND dissolved_at IS NULL))
);

CREATE TABLE convoy_member (
    convoy_id        bigint NOT NULL REFERENCES convoy(id) ON DELETE CASCADE,
    vessel_id        bigint NOT NULL REFERENCES vessel(id),
    role             text NOT NULL
                     CHECK (role IN ('lead','push','barge','towed')),
    position_in_unit smallint,
    PRIMARY KEY (convoy_id, vessel_id)
);
CREATE INDEX convoy_member_vessel_idx ON convoy_member (vessel_id);
;
CREATE TABLE position (
    vessel_id       bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    ts              timestamptz NOT NULL,
    -- az uzenet teljes azonositoja: az AIS `type` mezője (1-27) +
    -- a DAC/FID. A FI 10 a 6-os/8-as `msg_type` (a DAC 200, FID 10),
    -- a Class B a 21-es (a DAC 200, FID 21) → a `msg_type` ONMAGABAN
    -- nem eleg: a `msg_subtype` külonboztesti a belvízi FI 10-et a
    -- 8-as szabalyos uzenettől (a 04-es terv C-3 findingje).
    msg_type        smallint,
    msg_subtype     smallint,
    geom            geometry(Point,4326),
    sog_mps         numeric(5,2),
    cog_deg         numeric(5,2),
    heading_deg     numeric(5,2),
    nav_status      text
                    -- a szoveges AIS navigacios allapot (a 04-es terv
                    -- szerint a Pydantic-modell `Optional[str]`):
                    -- 'under way using engine', 'at anchor',
                    -- 'not under command', 'restricted manoeuvrability',
                    -- 'constrained by her draught', 'moored',
                    -- 'aground', 'engaged in fishing',
                    -- 'under way sailing', 'reserved (HSC)',
                    -- 'reserved (WIG)', 'power-driven vessel towing astern',
                    -- 'power-driven vessel pushing ahead',
                    -- 'power-driven vessel towing alongside',
                    -- 'reserved for future amendment of navigational status
                    -- for ships carrying DG, HS, or MP, or IMO hazard or
                    -- pollutant category C, high speed craft',
                    -- 'power-driven vessel towing astern',
                    -- 'undefined'
                    CHECK (nav_status IS NULL OR nav_status IN (
                      'under way using engine', 'at anchor',
                      'not under command', 'restricted manoeuvrability',
                      'constrained by her draught', 'moored',
                      'aground', 'engaged in fishing',
                      'under way sailing', 'reserved (HSC)',
                      'reserved (WIG)',
                      'power-driven vessel towing astern',
                      'power-driven vessel pushing ahead',
                      'power-driven vessel towing alongside',
                      'reserved for future amendment of navigational status',
                      'undefined')),
    rot_deg         numeric(5,2),
    ais_accuracy_m  numeric(6,1),
    lat_e7          integer,
    lon_e7          integer,
    river_km        numeric(8,3),        -- a **pozíció** üzenet fairway
                                    -- hectometre mezőjéből (a 04-es
                                    -- terv §4.5 pontosítja: a FI 10 a
                                    -- STATIKUS üzenet, a river_km a
                                    -- szokásos pozíció kiterjesztése)
    river_section_id bigint REFERENCES river_section(id),
    basin_id        bigint REFERENCES basin(id),
    shoreline_km    numeric(8,3),        -- a Balaton partkm-je
    source_id       bigint REFERENCES data_source(id),
    source_kind     text NOT NULL DEFAULT 'ais'
                    CHECK (source_kind IN ('ais','derived','manual')),
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (vessel_id, ts),
    -- **Az ertektartomany-ellenorizesek** (P1-23): a hajo mozgas
    -- adatai fizikai hatarok kozt vannak. A hibas AIS-uzenet
    -- (a decoder csukaszolas, a hibas NMEA) nem szabad beirni.
    CONSTRAINT position_sog_check CHECK (sog_mps IS NULL OR sog_mps BETWEEN 0 AND 60),
    CONSTRAINT position_cog_check CHECK (cog_deg IS NULL OR cog_deg >= 0 AND cog_deg < 360),
    CONSTRAINT position_heading_check CHECK (heading_deg IS NULL OR heading_deg >= 0 AND heading_deg < 360),
    CONSTRAINT position_lat_check CHECK (lat_e7 IS NULL OR lat_e7 BETWEEN -900000000 AND 900000000),
    CONSTRAINT position_lon_check CHECK (lon_e7 IS NULL OR lon_e7 BETWEEN -1800000000 AND 1800000000),
    CONSTRAINT position_river_km_check CHECK (river_km IS NULL OR river_km >= 0),
    CONSTRAINT position_shoreline_km_check CHECK (shoreline_km IS NULL OR shoreline_km >= 0)
) PARTITION BY RANGE (ts);
;
-- a havi particiok (a 0008_partitions.sql migracio)
CREATE TABLE position_p20261101 PARTITION OF position
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
-- ... a további honapok, a belepo fuggveny generálja

-- a DEFAULT particio: ha a heti drop_expired_partitions utan egy
-- ujonnan beallt honapnak meg nincs particioja, az INSERT ne bukjon el
CREATE TABLE position_default PARTITION OF position DEFAULT;
;
-- a default particio szuresen belul
DELETE FROM position_default
WHERE ts < now() - interval '90 days';
;
CREATE TABLE ais_message_raw (
    id           bigint GENERATED ALWAYS AS IDENTITY,
    vessel_id    bigint REFERENCES vessel(id) ON DELETE SET NULL,
    received_at  timestamptz NOT NULL,
    msg_type     smallint,
    raw_nmea     text NOT NULL,
    -- **A dedup-kulcs** (V-N-5): az `id` mindig uj
    -- (`GENERATED ALWAYS AS IDENTITY`), ezert a nyers uzenetek
    -- deduplicacioja nem arra epulhet. A README 6.2 dedup-kulcsa
    -- `(mmsi, ts, msg_type, sog, cog, lat, lon)` **nyers uzenetnel
    -- nem elerheto** (a parser meg nem bontotta) — a nyers NMEA
    -- tartalma alapjan szamitunk egy hash-t.
    --
    -- **A hash-t az INGEST szamitja** (a service retegen,
    -- Python `hashlib.sha256`), nem a DB. A DB-beli generalt
    -- oszlop nem mukodne: a `timestamptz::text` a session
    -- timezone-tol fugg (nem immutable), a `digest()`-hoz pedig a
    -- `pgcrypto` extension kellene. A hash a `raw_nmea` +
    -- `received_at` (epoch) + `source_id` elemeiből jon.
    msg_hash     bytea NOT NULL,
    source_id    bigint REFERENCES data_source(id),
    PRIMARY KEY (id, received_at)
) PARTITION BY RANGE (received_at);

-- A dedup egyedisegi indexe. **A particios kulcsot is tartalmaznia
-- kell** (a Postgres egy particionalt tablan a unique indexet csak
-- a particios kulccsal egyutt engedi).
CREATE UNIQUE INDEX ais_message_raw_hash_uniq
    ON ais_message_raw (msg_hash, received_at);

-- **A DEFAULT partíció KÖTELEZŐ** (V-C-1): a havi partíciókat a
-- `pg_cron` hozza létre, de az első INSERT előtt (vagy a partíciók
-- eldobása után) a tába üres partíció nélkül marad -> az ingest
-- "no partition of relation found for row" hibával elbukik.
-- A DEFAULT partíció ezt megelezi.
CREATE TABLE ais_message_raw_default PARTITION OF ais_message_raw DEFAULT;
;
-- A vízállás-mérések (R1: a kikötő-adatlapokhoz kell a szinttörténet)
CREATE TABLE water_level (
    gauge_id  bigint NOT NULL REFERENCES gauge(id) ON DELETE CASCADE,
    ts        timestamptz NOT NULL,
    level_cm  numeric(8,2) NOT NULL,
    PRIMARY KEY (gauge_id, ts)
) PARTITION BY RANGE (ts);
CREATE INDEX water_level_brin ON water_level USING BRIN (ts);

-- A DEFAULT particio (V-C-1) — lásd az ais_message_raw-nál
CREATE TABLE water_level_default PARTITION OF water_level DEFAULT;

-- A zsilip karbantartási / zárási idősor (R1: a kikötőrendhez tartozik)
CREATE TABLE lock_status (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lock_id    bigint NOT NULL REFERENCES lock(id) ON DELETE CASCADE,
    status     text NOT NULL
               CHECK (status IN ('open','closed','maintenance','restricted')),
    valid_from timestamptz NOT NULL,
    valid_to   timestamptz,
    note       text,
    source     text NOT NULL DEFAULT 'notice'
               CHECK (source IN ('notice','operator','manual'))
);
CREATE INDEX lock_status_lock_idx ON lock_status (lock_id, valid_from DESC);

-- A Balatoni heti menetrend (a README szerint R3)
CREATE TABLE vessel_schedule (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id      bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    route_id       bigint NOT NULL REFERENCES route(id),
    weekday        smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    departure_time time NOT NULL,
    valid_from     date,
    valid_to       date
);
CREATE INDEX vessel_schedule_vessel_idx ON vessel_schedule (vessel_id, weekday);

-- A közösségi pozíció-jelentés (R2: a figyelőlistával együtt)
CREATE TABLE position_report (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     bigint NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    vessel_id   bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    observed_ts timestamptz NOT NULL,
    geom        geometry(Point,4326),
    note        text,
    status      text NOT NULL DEFAULT 'new'
                CHECK (status IN ('new','accepted','rejected'))
);
CREATE INDEX position_report_status_idx ON position_report (status, observed_ts DESC);
;
CREATE VIEW vessel_verification AS
SELECT
    v.id AS vessel_id,
    CASE
        -- AIS-azonosított: van ENI vagy IMO, AIS-eredetű
        -- (**A `mmsi` NEM benne** -> különben az `ais_partial` ág
        -- halott kód lenne, lásd a megjegyzést alább)
        WHEN EXISTS (
            SELECT 1 FROM vessel_identifier i
            WHERE i.vessel_id = v.id
              AND i.valid_to IS NULL
              AND i.identifier_type IN ('eni','imo')
              AND i.origin = 'ais'
        ) THEN 'ais_identified'
        -- AIS-részleges: van MMSI, de nincs ENI/IMO
        WHEN EXISTS (
            SELECT 1 FROM vessel_identifier i
            WHERE i.vessel_id = v.id
              AND i.valid_to IS NULL
              AND i.identifier_type = 'mmsi'
              AND i.origin = 'ais'
        ) THEN 'ais_partial'
        -- Üzemeltető igazolta: van operator_claimed eredet
        WHEN EXISTS (
            SELECT 1 FROM vessel_data_origin o
            WHERE o.vessel_id = v.id
              AND o.is_current
              AND o.origin = 'operator_claimed'
        ) THEN 'operator_claimed'
        -- Név alapján (a mérésben a hajók 99,6%-a ez)
        WHEN v.sort_name <> '' THEN 'name_only'
        -- Forrás nélkül
        ELSE 'unverified'
    END::text AS computed_verification_level,
    -- az eltérés, ha a beirt ertek nem egyezik a szamitottal
    (v.verification_level <>
     CASE
        WHEN EXISTS (SELECT 1 FROM vessel_identifier i
                     WHERE i.vessel_id = v.id AND i.valid_to IS NULL
                       AND i.identifier_type IN ('eni','imo')
                       AND i.origin = 'ais') THEN 'ais_identified'
        WHEN EXISTS (SELECT 1 FROM vessel_identifier i
                     WHERE i.vessel_id = v.id AND i.valid_to IS NULL
                       AND i.identifier_type = 'mmsi'
                       AND i.origin = 'ais') THEN 'ais_partial'
        WHEN EXISTS (SELECT 1 FROM vessel_data_origin o
                     WHERE o.vessel_id = v.id AND o.is_current
                       AND o.origin = 'operator_claimed') THEN 'operator_claimed'
        WHEN v.sort_name <> '' THEN 'name_only'
        ELSE 'unverified'
     END) AS is_stale
FROM vessel v;
;
-- A legfrissebb pozíció hajonkent (a README 3.3/C szerint)
CREATE VIEW vessel_last_position AS
SELECT DISTINCT ON (vessel_id)
       vessel_id,
       ts,
       geom,
       sog_mps,
       river_km,
       river_section_id,
       basin_id,
       shoreline_km,
       source_kind,          -- 'derived' a barkaknál (a 01-es terv §5.5)
       now() - ts AS age
FROM position
ORDER BY vessel_id, ts DESC;

-- A kikoto es a hajok kapcsolata (a F-CNT-07 szerint: "a kikotoadatlap
-- megmutatja, mely hajok erintik")
--
-- A funkcioleiras 6.1 szerint az "erintett kikotok" forrasa az
-- "AIS - cel UN/LOCODE" -> a hajo `destination_port_id`-je a cel
-- kikotore mutat. A nezeten keresztul a kikotoadatlap megkeresi:
--   - a celallomas alapjan (a `destination_port_id`)
--   - a hazai kikotonek alapjan (a `home_port_id`)
--
-- Az R1-ben a funkcioleiras szerint a kikotoadatlap "uzemeltetoket"
-- mutat (a hajok neve helyett) -> a nezet a `vessel.operator_id`-t
-- is adja.
CREATE VIEW port_vessel AS
SELECT p.id                AS port_id,
       p.code              AS port_code,
       p.unlocode          AS port_unlocode,
       p.port_type,
       v.id                AS vessel_id,
       v.slug              AS vessel_slug,
       v.sort_name         AS vessel_name,   -- a hivatalos latin nev (a 02 §5.3)
       v.operator_id,
       'destination'::text AS relation
FROM port p
JOIN vessel v ON v.destination_port_id = p.id
UNION ALL
SELECT p.id, p.code, p.unlocode, p.port_type,
       v.id, v.slug, v.sort_name, v.operator_id,
       'home'::text
FROM port p
JOIN vessel v ON v.home_port_id = p.id;
;
ALTER TABLE vessel ADD COLUMN last_position_ts timestamptz;
ALTER TABLE vessel ADD COLUMN last_river_km numeric(8,3);

-- **A „leggyakoribb vízi szakasz"** (a `prof` reviewer C-1 findingje
-- után). A F-CAT-08 (M, R1) a „vízterület (Duna-szakasz /
-- Balaton-medence)" szűrőt kéri, de a `vessel` táblában eddig nem
-- volt szakasz-hivatkozás — a `position` pedig 90 napos TTL-lel
-- particionált (a szűrő a szezon vége felé üres eredményt adna).
-- Az ingest ezt a két mezőt tölti be, ugyanabban a tranzakcióban,
-- mint a `last_position_ts`/`last_river_km`.
ALTER TABLE vessel ADD COLUMN home_river_section_id bigint
    REFERENCES river_section(id);
ALTER TABLE vessel ADD COLUMN home_basin_id bigint
    REFERENCES basin(id);

-- A vízi terület szűrőjének indexe (a F-CAT-08)
CREATE INDEX vessel_area_home_section_idx
    ON vessel (operating_area, home_river_section_id)
    WHERE home_river_section_id IS NOT NULL;
CREATE INDEX vessel_area_home_basin_idx
    ON vessel (operating_area, home_basin_id)
    WHERE home_basin_id IS NOT NULL;
;
-- A kulcs nyelvenkenti szovege + a publikalasi munkafolyamat
CREATE TABLE content_text (
    content_key  text NOT NULL REFERENCES content_key(key) ON DELETE CASCADE,
    lang         char(2) NOT NULL REFERENCES language(code),
    text         text NOT NULL,
    status       text NOT NULL DEFAULT 'draft'
                 CHECK (status IN ('draft','review','published')),
    author_id    bigint REFERENCES app_user(id),
    reviewed_by  bigint REFERENCES app_user(id),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (content_key, lang)
);
CREATE INDEX content_text_status_idx ON content_text (status);

-- A forditoi feladatlista
CREATE TABLE translation_task (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_key  text NOT NULL REFERENCES content_key(key) ON DELETE CASCADE,
    lang         char(2) NOT NULL REFERENCES language(code),
    status       text NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open','in_progress','done','rejected')),
    assignee_id  bigint REFERENCES app_user(id),
    due_at       timestamptz,
    -- Egy kulcs-nyelv parra csak EGY forditoi feladat (P1-20)
    UNIQUE (content_key, lang)
);
CREATE INDEX translation_task_open_idx
    ON translation_task (status, due_at) WHERE status IN ('open','in_progress');

-- A kódkatalógusok (a README FK-val hivatkozik nekik)
CREATE TABLE notice_type (
    code       text PRIMARY KEY,
    name_key   text NOT NULL REFERENCES content_key(key),
    severity_default text NOT NULL DEFAULT 'info'
               CHECK (severity_default IN ('info','warning','error','critical'))
);

CREATE TABLE event_type (
    code       text PRIMARY KEY,
    name_key   text NOT NULL REFERENCES content_key(key),
    severity_default text NOT NULL DEFAULT 'info'
               CHECK (severity_default IN ('info','warning','error','critical'))
);

CREATE TABLE article_category (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code       text NOT NULL UNIQUE,
    name_key   text NOT NULL REFERENCES content_key(key)
);

-- A hivatalos ertesites (kikotorend, vizallasi hirdemeny)
CREATE TABLE notice (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    notice_type     text NOT NULL REFERENCES notice_type(code),
    source_authority text,
    source_url      text,
    reference_no    text,
    valid_from      timestamptz,
    valid_to        timestamptz,
    river_km_from   numeric(8,3),
    river_km_to     numeric(8,3),
    geom            geometry(Point,4326),
    severity        text NOT NULL DEFAULT 'info'
                    CHECK (severity IN ('info','warning','error','critical')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX notice_valid_idx ON notice (valid_from, valid_to);
CREATE INDEX notice_geom_gix ON notice USING GIST (geom);

CREATE TABLE notice_i18n (
    notice_id bigint NOT NULL REFERENCES notice(id) ON DELETE CASCADE,
    lang      char(2) NOT NULL REFERENCES language(code),
    title     text NOT NULL,
    body      text,
    PRIMARY KEY (notice_id, lang)
);

-- Az esemeny (fajlagos esemeny: kozlekedesi, vizallasi, karbantartas)
CREATE TABLE event (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type text NOT NULL REFERENCES event_type(code),
    severity   text NOT NULL DEFAULT 'info'
               CHECK (severity IN ('info','warning','error','critical')),
    geom       geometry(Point,4326),
    river_km   numeric(8,3),
    starts_at  timestamptz NOT NULL,
    ends_at    timestamptz,
    port_id    bigint REFERENCES port(id),
    vessel_id  bigint REFERENCES vessel(id),
    source     text NOT NULL DEFAULT 'notice'
               CHECK (source IN ('notice','operator','manual','ais_derived')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at IS NULL OR ends_at >= starts_at)
);
CREATE INDEX event_starts_idx ON event (starts_at DESC);
CREATE INDEX event_geom_gix ON event USING GIST (geom);

CREATE TABLE event_i18n (
    event_id    bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    lang        char(2) NOT NULL REFERENCES language(code),
    title       text NOT NULL,
    description text,
    PRIMARY KEY (event_id, lang)
);

-- A blog / cikk
CREATE TABLE article (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug              text NOT NULL UNIQUE,
    category_id       bigint NOT NULL REFERENCES article_category(id),
    author_id         bigint REFERENCES app_user(id),
    published_at      timestamptz,
    hero_image_url    text,
    status            text NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','review','published','archived')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX article_status_idx ON article (status, published_at DESC);

CREATE TABLE article_i18n (
    article_id       bigint NOT NULL REFERENCES article(id) ON DELETE CASCADE,
    lang             char(2) NOT NULL REFERENCES language(code),
    title            text NOT NULL,
    summary          text,
    body_md          text,
    meta_title       text,
    meta_description text,
    PRIMARY KEY (article_id, lang)
);
CREATE INDEX article_i18n_title_trgm ON article_i18n USING GIN (title gin_trgm_ops);
;
-- A mértékegységek (a hajóméretek SI-alapúak, de a formázás
-- kliensoldali — a README 4.6; ez a tábla a formázás
-- referencia-halmaza, nem a konverzió motorja)
CREATE TABLE unit (
    code         text PRIMARY KEY,        -- 'm', 'km', 't', 'kw', 'TEU'
    name_key     text NOT NULL,
    quantity_kind text NOT NULL
                 CHECK (quantity_kind IN
                   ('length','mass','volume','power','capacity','speed')),
    to_base      numeric(12,6) NOT NULL DEFAULT 1,
    decimals     smallint NOT NULL DEFAULT 2
);

-- A pénznem (az R1-ben nincs pénznem-alapú adat — a README 2.8
-- a devizaárfolyamot említi, de a hajóadatok nem pénzügyiek;
-- a tábla a jövőbeli B2B API (R5) számára van, nem R1-kötelező)
CREATE TABLE currency (
    code          char(3) PRIMARY KEY,     -- ISO 4217
    name_key      text NOT NULL,
    decimals      smallint NOT NULL DEFAULT 2
);

CREATE TABLE fx_rate (
    base_currency  char(3) NOT NULL REFERENCES currency(code),
    quote_currency char(3) NOT NULL REFERENCES currency(code),
    rate_date      date NOT NULL,
    rate           numeric(18,8) NOT NULL,
    source_id      bigint REFERENCES data_source(id),
    PRIMARY KEY (base_currency, quote_currency, rate_date)
);
;
CREATE TABLE ais_gap (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vessel_id   bigint NOT NULL REFERENCES vessel(id) ON DELETE CASCADE,
    from_ts     timestamptz NOT NULL,
    to_ts       timestamptz,
    reason      text NOT NULL
                CHECK (reason IN
                  ('no_signal','in_port','out_of_coverage',
                   'receiver_failure','parser_error','unknown')),
    detected_at timestamptz NOT NULL DEFAULT now(),
    CHECK (to_ts IS NULL OR to_ts >= from_ts)
);
CREATE INDEX ais_gap_vessel_idx ON ais_gap (vessel_id, from_ts DESC);
CREATE INDEX ais_gap_open_idx ON ais_gap (detected_at DESC)
    WHERE to_ts IS NULL;
;
-- A saját AIS vevőhálózat telephelyei
CREATE TABLE ais_receiver_site (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code              text NOT NULL UNIQUE,     -- 'BUD-TETO'
    name              text NOT NULL,
    waterway_id       bigint NOT NULL REFERENCES waterway(id),
    river_km          numeric(8,3),
    geom              geometry(Point,4326),
    antenna_height_m  numeric(5,1),
    installed_at      date,
    operator_name     text,
    status            text NOT NULL DEFAULT 'planned'
                      CHECK (status IN ('planned','active','maintenance','retired')),
    last_seen_at      timestamptz,               -- a heartbeatből
    coverage_note     text,
    source_id         bigint REFERENCES data_source(id)
);
CREATE INDEX ais_receiver_site_geom_gix ON ais_receiver_site USING GIST (geom);
CREATE INDEX ais_receiver_site_status_idx ON ais_receiver_site (status);

-- A hibák nem esnek el csendben (README 6.2): a dead-letter
-- A `job_run` a `data_quality_event` ELOTT jön (FK-ordering: a
-- dead-letter a futashoz kotthet)
CREATE TABLE job_run (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_name   text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at   timestamptz,
    status     text NOT NULL DEFAULT 'running'
               CHECK (status IN ('running','success','failed','partial')),
    rows_in    integer,
    rows_out   integer,
    error_text text
);
CREATE INDEX job_run_name_idx ON job_run (job_name, started_at DESC);
CREATE INDEX job_run_failed_idx ON job_run (started_at DESC)
    WHERE status IN ('failed','partial');

CREATE TABLE data_quality_event (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- A kapcsolodo feldolgozasi futas (P1-26): a dead-letter sorok
    -- a futashoz kotthetok — anelkul nem derul ki, melyik ingest
    -- futas hagyott maga utan hibas sorokat.
    job_run_id   bigint REFERENCES job_run(id) ON DELETE SET NULL,
    source_id   bigint REFERENCES data_source(id),
    entity_type text,
    entity_id   bigint,
    severity    text NOT NULL DEFAULT 'warning'
                CHECK (severity IN ('info','warning','error','critical')),
    detected_at timestamptz NOT NULL DEFAULT now(),
    -- **A `reason` NEM külön oszlop** — a hiba nemét a `severity`
    -- hordozza, a konkrét okot (pl. 'parser_error: checksum mismatch')
    -- a `detail` szabad szövegben. (A 04-es terv C-4 findingje:
    -- a `reason='parser_error'` írás `column does not exist` hibával
    -- elhalna.)
    detail      text,
    resolved_at timestamptz
);
CREATE INDEX data_quality_event_open_idx
    ON data_quality_event (severity, detected_at DESC) WHERE resolved_at IS NULL;

-- A feldolgozasi futasok naploja
-- A feature flag-ek (a keszitesi fokozatokhoz)
CREATE TABLE feature_flag (
    key         text PRIMARY KEY,
    enabled     boolean NOT NULL DEFAULT false,
    rollout_pct smallint NOT NULL DEFAULT 100
               CHECK (rollout_pct BETWEEN 0 AND 100),
    variants    jsonb
);
;
-- A visszajelzes (F-DET-11): az anonim kozossegi jelzes is ide fut
CREATE TABLE feedback (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    bigint REFERENCES app_user(id) ON DELETE SET NULL,
    -- **A hivatkozott hajo** (a 06-os terv Q1): a F-DET-11 a
    -- felhasznalo egy KONKRET hajo hibajara vonatkozik — a
    -- visszajelzesnek meg kell neveznie, melyik hajorol van szo.
    -- A publikus API a `slug` alapjan tolti be (a slug a
    -- megfelelo hajot adja meg).
    vessel_id  bigint REFERENCES vessel(id) ON DELETE SET NULL,
    -- A `subject` a VISSZAJELZES targya (a `category` a tipusa) —
    -- a ketto kulonboztes a 06-os terv Q2-je szerint.
    subject    text NOT NULL DEFAULT 'other'
               CHECK (subject IN
                 ('data_correction','translation','map','source',
                  'feature','other')),
    category   text NOT NULL DEFAULT 'other'
               CHECK (category IN
                 ('data_correction','translation','map','source',
                  'feature','other')),
    body       text NOT NULL,
    status     text NOT NULL DEFAULT 'new'
               CHECK (status IN ('new','accepted','rejected')),
    created_at timestamptz NOT NULL DEFAULT now(),
    handled_by bigint REFERENCES app_user(id),
    handled_at timestamptz,
    -- a statusz es a kezeles osszhangja
    CHECK ((status = 'new' AND handled_at IS NULL)
           OR (status <> 'new' AND handled_at IS NOT NULL))
);
CREATE INDEX feedback_open_idx ON feedback (created_at DESC)
    WHERE handled_at IS NULL;
CREATE INDEX feedback_vessel_idx ON feedback (vessel_id)
    WHERE vessel_id IS NOT NULL;
CREATE INDEX feedback_claims_idx ON feedback (created_at DESC)
    WHERE category = 'data_correction' AND status = 'new';

CREATE TABLE audit_log (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id   bigint REFERENCES app_user(id),
    action     text NOT NULL
               CHECK (action IN ('INSERT','UPDATE','DELETE','IMPORT')),
    entity_type text NOT NULL,
    entity_id   bigint,
    before      jsonb,
    after       jsonb,
    at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_entity_idx ON audit_log (entity_type, entity_id, at DESC);
CREATE INDEX audit_log_actor_idx ON audit_log (actor_id, at DESC);
;
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_vessel_updated_at
    BEFORE UPDATE ON vessel
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
;
CREATE OR REPLACE FUNCTION validate_route_cargo_types() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_invalid text;
BEGIN
    IF NEW.cargo_types IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT array_agg(c ORDER BY c) INTO v_invalid
    FROM unnest(NEW.cargo_types) AS c
    WHERE NOT EXISTS (SELECT 1 FROM cargo_type WHERE code = c);

    IF v_invalid IS NOT NULL THEN
        RAISE EXCEPTION
            'Ismeretlen rakomanytipus a route.cargo_types-ben: % '
            '(a cargo_type.code ertekek hasznalhatok)',
            v_invalid;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_route_cargo_types_valid
    BEFORE INSERT OR UPDATE OF cargo_types ON route
    FOR EACH ROW EXECUTE FUNCTION validate_route_cargo_types();
;
CREATE OR REPLACE FUNCTION guard_role_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.role IS DISTINCT FROM OLD.role THEN
        -- az admin szerep allitja be a sessionben
        IF current_setting('app.user_role', true) IS DISTINCT FROM 'admin' THEN
            RAISE EXCEPTION
                'A szerepváltas csak az admin szamara engedélyezett '
                '(a beallitott szerep: %)',
                COALESCE(current_setting('app.user_role', true), '<nincs>');
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_app_user_guard_role
    BEFORE UPDATE OF role ON app_user
    FOR EACH ROW EXECUTE FUNCTION guard_role_change();
;
-- A vessel_i18n -> vessel.sort_name szinkron (a hajonev nem fordul,
-- ezért a 'hu' nyelv hivatalos neve az rendezesi kulcs)
CREATE OR REPLACE FUNCTION sync_vessel_sort_name() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.lang = 'hu' THEN
        UPDATE vessel
        SET sort_name = lower(unaccent(NEW.name))
        WHERE id = NEW.vessel_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_vessel_i18n_sort_name
    AFTER INSERT OR UPDATE OF name ON vessel_i18n
    FOR EACH ROW EXECUTE FUNCTION sync_vessel_sort_name();
;
CREATE OR REPLACE FUNCTION audit_row_change() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_actor  bigint;
    v_entity bigint;
    v_old    jsonb;
    v_new    jsonb;
BEGIN
    -- A sessionben beallitott felhasznalo (a FastAPI middleware allitja be).
    --
    -- **V-N-6: ha nincs beallitva, a `v_actor` NULL marad** -> az
    -- audit-nyomvonalban nem lenne ki, ki valtozott. Az ingest
    -- (etl) nem a FastAPI-n keresztul jön, ezert a **rendszer
    --aktor** a megoldas: az `app_user` tablaban van egy dedikalt
    -- 'system' felhasznalo (a seed hozza letre), es az ingest
    -- sessionje azt allitja be (`SET app.user_id = <system id>`).
    --
    -- A **kezi szerkesztes** (a szerkesztoi felulet) mindig a
    -- tenyleges felhasznalo id-jet allitja be -> a NULL nem
    -- fordulhat elo.
    -- **A `current_setting` numerikus-biztos olvasasa** (P1-12):
    -- egy hibas session-ertek (`SET app.user_id='abc'`) a
    -- `::bigint` casttal MEGBUKTATNA minden auditot — a hiba
    -- nem a tranzakcioban, hanem a triggerben keletkezne.
    -- A `regexp_match` ellenoriz, a hibas ertek pedig NULL ->
    -- a 'system' aktorhoz esunk.
    v_actor := (
        SELECT (regexp_match(
            current_setting('app.user_id', true),
            '^\d+$'
        ))[1]::bigint
    );

    -- A biztonsagi háló: ha a session nem allitotta be, a
    -- dedikalt 'system' aktorhoz esunk (nem NULL).
    IF v_actor IS NULL THEN
        SELECT id INTO v_actor FROM app_user WHERE email = 'system@vessel-tracker.local';
    END IF;

    IF TG_OP = 'INSERT' THEN
        v_old := NULL;
        v_new := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_old := to_jsonb(OLD);
        v_new := to_jsonb(NEW);
        -- csak akkor logolunk, ha valtozott
        IF v_old = v_new THEN
            RETURN NEW;
        END IF;
    ELSE
        v_old := to_jsonb(OLD);
        v_new := NULL;
    END IF;

    -- Az entity_id a **PK oszlopokbol** jon, nem egy fix 'id'
    -- mezobol (H-9): a `vessel_i18n`/`port_i18n` nincs `id` oszlopuk
    -- (a PK: (vessel_id, lang) / (port_id, lang)) → a korabbi
    -- megoldas NULL entity_id-t irt minden forditas-modositásra.
    v_entity := COALESCE(
        (to_jsonb(NEW)->>'vessel_id')::bigint,
        (to_jsonb(OLD)->>'vessel_id')::bigint,
        (to_jsonb(NEW)->>'port_id')::bigint,
        (to_jsonb(OLD)->>'port_id')::bigint,
        (to_jsonb(NEW)->>'id')::bigint,
        (to_jsonb(OLD)->>'id')::bigint
    );

    INSERT INTO audit_log (actor_id, action, entity_type, entity_id, before, after)
    VALUES (v_actor, TG_OP, TG_TABLE_NAME, v_entity, v_old, v_new);

    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_vessel_audit
    AFTER INSERT OR UPDATE OR DELETE ON vessel
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_vessel_i18n_audit
    AFTER INSERT OR UPDATE OR DELETE ON vessel_i18n
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_port_audit
    AFTER INSERT OR UPDATE OR DELETE ON port
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_port_i18n_audit
    AFTER INSERT OR UPDATE OR DELETE ON port_i18n
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_vessel_cert_audit
    AFTER INSERT OR UPDATE OR DELETE ON vessel_cert
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_vessel_service_period_audit
    AFTER INSERT OR UPDATE OR DELETE ON vessel_service_period
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

-- **A további, kézzel módosítható referenciatáblák** (P1-27):
-- a README 7.4 szerint *minden* felhasználó által módosítható
-- referenciaadat-változás az audit_log-ba kerül. A lista a
-- szerkesztői felület által módosítható entitásokat fedi le
-- (a `06` – Szerkesztői felület terv a teljes listát rögzíti).
CREATE TRIGGER trg_notice_audit
    AFTER INSERT OR UPDATE OR DELETE ON notice
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_notice_i18n_audit
    AFTER INSERT OR UPDATE OR DELETE ON notice_i18n
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_event_audit
    AFTER INSERT OR UPDATE OR DELETE ON event
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_event_i18n_audit
    AFTER INSERT OR UPDATE OR DELETE ON event_i18n
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_article_audit
    AFTER INSERT OR UPDATE OR DELETE ON article
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_article_i18n_audit
    AFTER INSERT OR UPDATE OR DELETE ON article_i18n
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_content_text_audit
    AFTER INSERT OR UPDATE OR DELETE ON content_text
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_route_audit
    AFTER INSERT OR UPDATE OR DELETE ON route
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_route_i18n_audit
    AFTER INSERT OR UPDATE OR DELETE ON route_i18n
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_basin_audit
    AFTER INSERT OR UPDATE OR DELETE ON basin
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_waterway_audit
    AFTER INSERT OR UPDATE OR DELETE ON waterway
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_operator_audit
    AFTER INSERT OR UPDATE OR DELETE ON operator
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_vessel_type_audit
    AFTER INSERT OR UPDATE OR DELETE ON vessel_type
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_cargo_type_audit
    AFTER INSERT OR UPDATE OR DELETE ON cargo_type
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_marina_audit
    AFTER INSERT OR UPDATE OR DELETE ON marina
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_berth_audit
    AFTER INSERT OR UPDATE OR DELETE ON berth
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_terminal_audit
    AFTER INSERT OR UPDATE OR DELETE ON terminal
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_gauge_audit
    AFTER INSERT OR UPDATE OR DELETE ON gauge
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();

CREATE TRIGGER trg_river_section_audit
    AFTER INSERT OR UPDATE OR DELETE ON river_section
    FOR EACH ROW EXECUTE FUNCTION audit_row_change();
;
CREATE OR REPLACE FUNCTION drop_expired_partitions(
    p_table     text,
    p_keep_days integer
) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    r          record;
    v_dropped  integer := 0;
    v_boundary date := (now() - (p_keep_days || ' days')::interval)::date;
BEGIN
    FOR r IN
        SELECT c.relname AS partition_name,
               -- a particio TARTOMANYANAK VEGE (a pg_get_expr-bol nem
               -- olvasunk, hanem a nevebol szamolunk — a konvencio:
               -- <tabla>_pYYYYMMDD, a hataridot a NEV eleje jelzi)
               to_date(substring(c.relname FROM '_p(\d{8})$'), 'YYYYMMDD')
                   + interval '1 day' AS range_end
        FROM pg_class c
        JOIN pg_inherits i ON i.inhrelid = c.oid
        JOIN pg_class p ON p.oid = i.inhparent
        JOIN pg_namespace n ON n.oid = p.relnamespace
        WHERE n.nspname = 'public'
          AND p.relname = p_table
          AND c.relname ~ ('^' || p_table || '_p\d{8}$')
          -- A DEFAULT particiot SOHA nem dobjuk el (V-C-1): az
          -- ingest ne bukjon el egy hataridot el nem er
          -- particio hianyaban
          AND c.relname NOT LIKE '%_default'
    LOOP
        -- **A hatar a particio TARTOMANYANAK VEGE, nem a kezdete**
        -- (V-C-6): a havi particio p20261101 a 2026-11-01 datumot
        -- jelzi, ami egy 14 napos TTL hatarral egyutt mar REGEN
        -- eldobhatna a 2 napos, aktualis adatot is.
        -- A napi particiokkal (<tabla>_p20261118) a TTL pontos:
        -- a hatarido = a particio kezdete + 1 nap.
        BEGIN
            IF r.range_end::date < v_boundary THEN
                EXECUTE format('DROP TABLE %I', r.partition_name);
                v_dropped := v_dropped + 1;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- a nev nem illeszkedik a mintara: kihagyjuk, nem allunk meg
            CONTINUE;
        END;
    END LOOP;

    RETURN v_dropped;
END;
$$;
;
-- **A `sync_vessel_identifiers`** (a `vessel_identifier` AFTER trigger
-- hívja): UPDATE-el a `vessel` sort — a `vessel` azonosító oszlopait
-- az aktív primer azonosítókra állítva.
CREATE OR REPLACE FUNCTION sync_vessel_identifiers() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_vessel_id bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_vessel_id := OLD.vessel_id;
    ELSE
        v_vessel_id := NEW.vessel_id;
    END IF;

    UPDATE vessel v
    SET mmsi = src.mmsi, eni = src.eni, imo = src.imo
    FROM (
        SELECT
            max(value) FILTER (WHERE identifier_type = 'mmsi')::int AS mmsi,
            max(value) FILTER (WHERE identifier_type = 'eni')    AS eni,
            max(value) FILTER (WHERE identifier_type = 'imo')    AS imo
        FROM vessel_identifier
        WHERE vessel_id = v_vessel_id
          AND valid_to IS NULL
          AND is_primary
    ) src
    WHERE v.id = v_vessel_id;

    RETURN NULL;   -- AFTER trigger
END;
$$;

-- **A `sync_vessel_from_identifiers`** (a `vessel` BEFORE UPDATE
-- trigger hívja): a NEW-be betölti az aktuális értékeket — így a
-- `vessel` UPDATE no-op, és a lánc nem rekursál.
CREATE OR REPLACE FUNCTION sync_vessel_from_identifiers() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    SELECT
        max(value) FILTER (WHERE identifier_type = 'mmsi')::int,
        max(value) FILTER (WHERE identifier_type = 'eni'),
        max(value) FILTER (WHERE identifier_type = 'imo')
    INTO NEW.mmsi, NEW.eni, NEW.imo
    FROM vessel_identifier
    WHERE vessel_id = NEW.id
      AND valid_to IS NULL
      AND is_primary;

    RETURN NEW;
END;
$$;
;
-- **Két trigger, egy irány, NEM rekurzál.**
--
-- A `vessel_identifier` a **kanonikus** tároló (az idősorral),
-- a `vessel` oszlopai a **gyors olvasás**.
--
-- 1. `vessel_identifier` **AFTER** UPDATE/DELETE -> UPDATE-el a
--    `vessel` soron (a `vessel` oszlopai frissulnek)
-- 2. `vessel` **BEFORE** UPDATE -> a NEW-be betolti a
--    `vessel_identifier` aktualis ertekeit
--
-- **Miért nem rekurál?** A 2. trigger a NEW-be irja az aktualis
-- `vessel_identifier` erteket — igy a `vessel` UPDATE **no-op**
-- (az ertek mar ugyanaz), es a PostgreSQL nem indit ujabb
-- `vessel_identifier` triggert. A lan: vessel_identifier UPDATE ->
-- vessel UPDATE (a BEFORE trigger beallitja a NEW-et) -> VEGE.
--
-- **A korábbi ketiranyu megoldas rekuralt**: a `vessel` BEFORE
-- trigger UPDATE-elte a `vessel_identifier`-t, ami ujra meghivta
-- az AFTER triggert. A fenti megoldasban a `vessel` OLDALON nincs
-- ilyen trigger.
--
-- **A `vessel` INSERT** (a hajo letrehozasa) nem futtatja a BEFORE
-- UPDATE triggert -> **az ingest a `vessel_identifier`-be ir**
-- (a service retegen, egy tranzakcioban), es a `vessel` oszlopokat
-- a kod ugyancsak feltolti.

-- (1) a vessel_identifier -> vessel irany
CREATE TRIGGER trg_vessel_sync_identifiers
    AFTER INSERT OR UPDATE OF value, is_primary, valid_to
        ON vessel_identifier
    FOR EACH ROW EXECUTE FUNCTION sync_vessel_identifiers();

CREATE TRIGGER trg_vessel_sync_identifiers_del
    AFTER DELETE ON vessel_identifier
    FOR EACH ROW EXECUTE FUNCTION sync_vessel_identifiers();

-- (2) a vessel BEFORE trigger: a NEW-be betolti az aktualis ertekeket
CREATE TRIGGER trg_vessel_from_identifiers
    BEFORE UPDATE ON vessel
    FOR EACH ROW EXECUTE FUNCTION sync_vessel_from_identifiers();
;
-- A pg_cron extension a custom Docker image-ben van (a 01-es terv §3.2)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- a nyers AIS-üzenetek 14 napos TTL-je
SELECT cron.schedule('drop-raw-partitions', '17 3 * * 1',
  $$SELECT drop_expired_partitions('ais_message_raw', 14)$$);

-- a vízállás-mérések 90 napos TTL-je
SELECT cron.schedule('drop-water-level-partitions', '23 3 * * 1',
  $$SELECT drop_expired_partitions('water_level', 90)$$);

-- A POSITION (a hajok poziciok) 90 napos TTL-je
-- **A blackboard X-3 findingje (a 05-09-es swarm review-bol):** a
-- `position` a legnagyobb particionalt tabla (~27 millio sor/hó a
-- meresbol, a 09 §8.1) → **a 90 napos TTL-nek is kell cron-job**,
-- kulonben a particiok **korlatanul gyarodnak** (a 02 §8.2 szerint
-- ez a legnagyobb tarhelyigeny).
SELECT cron.schedule('drop-position-partitions', '27 3 * * 1',
  $$SELECT drop_expired_partitions('position', 90)$$);
;
-- a szerepek (a README 7.3)
DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon','public_api','admin_api','app_user_role','editor','admin','etl','api_client']
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
    END LOOP;
END;
$$;

-- a publikus API csak az olvasást és a anonim írást látja
-- **Először mindent visszavonunk** — a `GRANT ... ON ALL TABLES`
-- öröklődne a későbbi migrációkból (a klasszikus hiba).
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon', r.tablename);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM public_api', r.tablename);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM admin_api', r.tablename);
    END LOOP;
END;
$$;

-- A **`public_api`** szerep: a weboldal DB-kapcsolata.
-- Az `anon` a *felhasználó* (a feedback) — külön szerep, külön jogosultság.
--
-- A publikus olvasás **explicit lista** — NEM `ON ALL TABLES`
-- (az `app_user` password_hash-e és session-hash-e, az
-- `ais_message_raw`, az `audit_log` és a `job_run` így nem publikus).
GRANT SELECT ON vessel, vessel_i18n, vessel_alias, vessel_identifier,
    vessel_type, vessel_type_i18n, vessel_data_origin,
    vessel_ownership, vessel_cert, vessel_service_period,
    port, port_i18n, berth, terminal, lock, lock_i18n, lock_status,
    operator, operator_i18n,
    basin, basin_i18n, marina, route, route_i18n, route_stop,
    cargo_type, cargo_type_i18n, notice, notice_i18n, notice_type,
    event, event_i18n, event_type, article, article_i18n, article_category,
    content_key, content_text,
    country, waterway, waterway_i18n, river_section, river_section_i18n,
    gauge, gauge_i18n, water_level, data_source
    TO public_api;

-- **Az `admin_api`** (a `06` – szerkesztői-terv §2.1a) — a szerkesztői
-- felület DB-kapcsolata. **A `public_api` NEM olvashatja az
-- `app_user`-t** (a session-hash nem publikus) → **külön szűk szerep**.
--
-- **A `USAGE` a `public` sémára KELL** — különben a szerep nem látja
-- az egyáltalán a táblákat („relation does not exist") → ez a
-- validátor füsttesztje fogta meg (a prof C-4 findingje).
GRANT USAGE ON SCHEMA public TO admin_api;
GRANT USAGE ON SCHEMA public TO public_api;
--
-- A `06` §2.1a szerint: a `session_token_hash` és a `session_expires_at`
-- olvasható, a `password_hash` **nem**.
GRANT SELECT (id, email, role, locale, unit_system, status,
               session_token_hash, session_expires_at)
    ON app_user TO admin_api;
-- a belepes a sessiont IRJA (a 06 §2.1 create_session)
GRANT UPDATE (session_token_hash, session_expires_at)
    ON app_user TO admin_api;

-- A `admin_api` a hajodata olvasasa mellett a **szerkesztoi
-- muveleteket** is vegezi (a F-ADM-02) → a hajok, a forrasok, a
-- nevek es a forditasok szinten kezelhetoek.
GRANT SELECT, UPDATE ON vessel, vessel_i18n, vessel_identifier,
    vessel_data_origin, vessel_type, vessel_type_i18n, content_text
    TO admin_api;
GRANT SELECT ON operator, operator_i18n, country, waterway_i18n,
    vessel_verification, vessel_last_position,
    vessel_data_origin_current, vessel_data_origin_conflicts
    TO admin_api;

-- **A NÉZETEKRE** a gronzás **külön kell** — a `GRANT SELECT ON
-- <table>` nem terjed ki a nézetekre (a PostgreSQL a nézetet a
-- definiáló táblák jogosultságait követi, de a `SELECT` közvetlenül
-- a nézetre külön kell).
GRANT SELECT ON vessel_verification, vessel_last_position,
    vessel_data_origin_current, vessel_data_origin_conflicts
    TO public_api;

-- A `position` a `vessel_last_position` nézet alaptáblája — a nézet
-- olvasása a `position` SELECT-jogát is igényli.
GRANT SELECT ON position TO public_api;

-- Az `anon` **csak** a visszajelzést írhatja (F-DET-11).
-- **A sequence-jogosultság is kell!** — a `feedback.id` GENERATED
-- ALWAYS AS IDENTITY, így az INSERT a `feedback_id_seq` USAGE-ét
-- igényli. Enélkül a `POST /api/v1/feedback` "permission denied"
-- hibával elbukna (a preshaz reviewer C-2 findingje).
GRANT INSERT ON feedback TO anon;
GRANT USAGE ON SEQUENCE feedback_id_seq TO anon;

-- A **`editor`** és az **`admin`**: minden referencia- és fordítási adat.
-- Az `editor` NEM módosíthatja az `app_user`-t (a jelszó-hash) és
-- az `audit_log`-ot (a naplót).
GRANT SELECT, INSERT, UPDATE, DELETE ON vessel, vessel_i18n, vessel_alias,
    vessel_identifier, vessel_data_origin, vessel_cert, vessel_service_period,
    vessel_ownership, vessel_type, vessel_type_i18n,
    port, port_i18n, berth, terminal, lock, lock_i18n,
    basin, basin_i18n, marina, route, route_i18n, route_stop,
    cargo_type, cargo_type_i18n, waterway, waterway_i18n,
    river_section, river_section_i18n, gauge, gauge_i18n,
    content_key, content_text, translation_task,
    notice, notice_i18n, notice_type, event, event_i18n, event_type,
    article, article_i18n, article_category,
    data_source, ais_receiver_site, lock_status, feedback
    TO editor;

-- Az **`admin`**: minden, DE az `audit_log`-ot NEM törölheti
-- (V-C-5) — az audit-nyomvonalat meg kell őrizni. Az `admin`
-- az `audit_log`-ot olvashatja és INSERT-elhet (a trigger miatt),
-- de a DELETE-RE nincs jogosultsága.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO admin;
REVOKE DELETE ON audit_log FROM admin;

-- Az **`etl`**: csak az ingest és az aggregáció (a README 7.3).
-- **Az `audit_log`-ba is írhat** (V-C-3): az `audit_row_change`
-- trigger a `vessel`/`vessel_i18n`/`port`/… módosításakor az
-- `audit_log`-ba ír — ha az `etl` nem tud oda írni, az ingest
-- MINDEN írása elbukik (a trigger hibája megszakítja a statementet).
GRANT SELECT, INSERT, UPDATE ON ais_message_raw, position, vessel,
    vessel_data_origin, vessel_identifier, job_run, data_quality_event,
    ais_gap, water_level TO etl;
GRANT INSERT ON audit_log TO etl;

-- Az **`app_user`** (a bejelentkezett felhasználó): a saját adatai.
-- **P1-30: a szerepnek volt a null gronzasa** — most van:
-- a felhasznalo a sajat profiljat olvashatja es módosithatja, de
-- az `app_user` TOBB sorát nem (a `WHERE id = current_user_id()`
-- a DB-szintu szűrés helyett a sessionben beállított
-- `app.user_id`-vel mukodik — a lásd §9.1).
GRANT SELECT, UPDATE ON app_user TO app_user_role;

-- Az **`api_client`** (R5, a B2B API): a szűk kimenetre való
-- olvasás. **R1-ben nincs B2B API**, de a szerep a semát
-- elhelyezi (a gronzas az R5-ben lesz konkrét).
GRANT SELECT ON vessel, vessel_i18n, port, port_i18n, position
    TO api_client;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO editor, admin, etl;

-- **A jövőbeli táblák** alapértelmezett jogosultsága — enélkül egy
-- új migrációban hozzáadott tábla automatikusan jogosítatlan marad
-- (a `GRANT ON ALL TABLES` csak egyszer futtatva fedi le).
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO public_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO editor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO admin;
;
-- A WAL-archivum a PITR alapja (a postgresql.conf-ban, nem a DB-ben)
-- archive_mode = on
-- archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'
;
-- =====================================================================
-- A REFERENCIAADATOK (a seed)
--
-- A schema hasznalhato-e a seed nelkul? NEM: a `vessel_type_i18n`,
-- a `vessel_i18n`, a `port_i18n` stb. mind a `language`-re mutat,
-- es a `vessel.vessel_type_code` a `vessel_type`-ra. A seed nelkul
-- a DB ures marad, es az ingest (a `vessel_type_code` kitoltes) elhal.
--
-- A `language` a legfontosabb: a `vessel_type_i18n` (a hajotipus
-- magyar neve), a `vessel_i18n` (a hajo neve) es a `content_text`
-- mind ezen keresztul fordul a nyelvre.
-- =====================================================================

INSERT INTO language (code, name_native, name_en, is_rtl)
VALUES ('hu', 'magyar', 'Hungarian', false),
       ('en', 'English', 'English', false),
       ('de', 'Deutsch', 'German', false);

-- A vizszonyatok (a 02-es terv 4.1a sza szerint: a szamok a
-- hivatkozott oszlopok)
INSERT INTO data_source
    (code, name, provider, license_type, license_ref, coverage_desc,
     quality_tier, is_primary, active)
VALUES ('own-ais-budapest', 'Sajat AIS-vevo (budapest)',
        'vessel-tracker', 'own', NULL,
        'Budapest, a Duna belso szakasza', 'a', true, true),
       ('own-ais-', 'Sajat AIS-vevo (tovabbi helyszinek)',
        'vessel-tracker', 'own', NULL,
        'A vevohalozat tovabbi telephelyei', 'a', false, true),
       ('operator-claim', 'Uzemeltetoi kozles',
        'a hajok uzemeltetoi', 'contractual', NULL,
        'Az uzemeltetok altal adott adatok', 'b', false, true),
       ('official', 'Hivatalos forras',
        'a hajozasi hatosagok', 'public', NULL,
        'A hivatalos nyilvantartasok', 'a', true, true),
       ('editorial', 'Szerkesztoi',
        'a vessel-tracker szerkesztoi', 'own', NULL,
        'A szerkesztoi munkaja', 'c', false, true);

-- A countries (a MMSI elolagja -> orszag; a 03-as terv szerint)
--
-- MEGJEGYZES: a `country` tablaban NINCS mmsi-prefix oszlop -> az
-- MMSI -> orszag meghatarozasa a `vessel_identifier`-ben (a 02-es
-- terv 5.3) vagy egy kod-tabla segitsegevel tortenik. A `HU` a
-- magyarorszagi, a `DUNA-UPPER` stb. a vizszonyati orszagok.
INSERT INTO country (code, name_local, eu_member)
VALUES ('HU', 'Magyarorszag', true),
       ('AT', 'Ausztria', true),
       ('DE', 'Nemetorszag', true),
       ('NL', 'Hollandia', true),
       ('FI', 'Finnorszag', true),
       ('FR', 'Franciaorszag', true),
       ('LU', 'Luxemburg', true),
       ('UA', 'Ukrajna', false),
       ('HR', 'Horvatorszag', true),
       ('RO', 'Romania', true),
       ('SK', 'Szlovakia', true),
       ('BG', 'Bulgaria', true),
       ('RS', 'Szerbia', false),
       ('SI', 'Szlovenia', true),
       ('BA', 'Bosznia-Hercegovina', false),
       ('GB', 'Egyesult Kiralysag', false),
       ('NO', 'Norvegia', true),
       ('SE', 'Svedorszag', true),
       ('DK', 'Dania', true),
       ('CH', 'Svájc', true),
       ('IT', 'Olaszorszag', true),
       ('CZ', 'Csehorszag', true),
       ('PL', 'Lengyelorszag', true),
       ('MD', 'Moldova', false);

-- A vizszonyatok (a foldrajzi nevtar: az elnevezesek es a szakaszok)
INSERT INTO waterway (code, waterway_type, length_km, is_active)
VALUES ('DUNA', 'main', 2850.0, true),
       ('BALATON', 'lake', 79.7, true);

INSERT INTO waterway_i18n (waterway_id, lang, name, description)
SELECT w.id, v.lang, v.name, v.description
FROM (VALUES
    ('DUNA', 'hu', 'Duna', 'A Duna folyo'),
    ('DUNA', 'en', 'Danube', 'The Danube river'),
    ('DUNA', 'de', 'Donau', 'Die Donau'),
    ('BALATON', 'hu', 'Balaton', 'A Balaton to'),
    ('BALATON', 'en', 'Lake Balaton', 'Lake Balaton'),
    ('BALATON', 'de', 'Balaton', 'Der Balaton')
) AS v(waterway_code, lang, name, description)
JOIN waterway w ON w.code = v.waterway_code;

-- A folyoszakaszok (a `river_section` — a hajok hazai szakasza)
INSERT INTO river_section
    (waterway_id, code, km_from, km_to, country_code, risk_level, max_draft_m, fairway_code)
SELECT w.id, v.code, v.km_from, v.km_to, 'HU', v.risk, v.draft, NULL
FROM (VALUES
    ('DUNA-01', 'DUNA', 1650.0, 1660.0, 'low', 9.0),
    ('DUNA-02', 'DUNA', 1660.0, 1690.0, 'low', 9.0),
    ('DUNA-03', 'DUNA', 1690.0, 1720.0, 'low', 8.5),
    ('DUNA-04', 'DUNA', 1720.0, 1750.0, 'low', 8.5),
    ('DUNA-05', 'DUNA', 1750.0, 1780.0, 'medium', 6.0),
    ('DUNA-06', 'DUNA', 1780.0, 1810.0, 'medium', 6.0),
    ('BAL-01', 'BALATON', 0.0, 15.0, 'low', 4.0),
    ('BAL-02', 'BALATON', 15.0, 40.0, 'low', 4.0),
    ('BAL-03', 'BALATON', 40.0, 60.0, 'low', 4.0),
    ('BAL-04', 'BALATON', 60.0, 75.0, 'low', 3.5),
    ('BAL-05', 'BALATON', 75.0, 95.0, 'low', 3.5)
) AS v(code, waterway_code, km_from, km_to, risk, draft)
JOIN waterway w ON w.code = v.waterway_code;

INSERT INTO river_section_i18n (river_section_id, lang, name, description)
SELECT r.id, v.lang, v.name, NULL
FROM (VALUES
    ('DUNA-01', 'hu', 'Budapest - Csepel'),
    ('DUNA-01', 'en', 'Budapest - Csepel'),
    ('DUNA-02', 'hu', 'Csepel - Adony'),
    ('DUNA-03', 'hu', 'Adony - Dunafoldvar'),
    ('DUNA-04', 'hu', 'Dunafoldvar - Szekszard'),
    ('DUNA-05', 'hu', 'Szekszard - Baja'),
    ('DUNA-06', 'hu', 'Baja - Mohacs'),
    ('BAL-01', 'hu', 'Keszthely'),
    ('BAL-02', 'hu', 'Siofok'),
    ('BAL-03', 'hu', 'Balatonfured'),
    ('BAL-04', 'hu', 'Tihany'),
    ('BAL-05', 'hu', 'Szarvas')
) AS v(code, lang, name)
JOIN river_section r ON r.code = v.code;

-- A medencek (a `basin` — a hajok medenceje)
--
-- A `basin.name_key` a `content_key`-re mutat (nem egy i18n-tabla),
-- ezert a kulcsokat a `content_key` seed-ben kell elhozni (a
-- `content_key` a UI-szovegek, a rendszeruzenetek es a sugo taroloja
-- a README 4.2 szerint).
INSERT INTO content_key (key, domain, description, source_lang, is_placeholder)
VALUES ('basin.duna_upper', 'ui', 'A Dunakulcs medence neve', 'hu', false),
       ('basin.duna_middle', 'ui', 'A Duna-kozep medence neve', 'hu', false),
       ('basin.duna_lower', 'ui', 'A Dunakozsog medence neve', 'hu', false),
       ('basin.balaton', 'ui', 'A Balatoni medence neve', 'hu', false);

INSERT INTO basin (waterway_id, code, name_key, geo_extent)
SELECT w.id, v.code, v.name_key, NULL
FROM (VALUES
    ('DUNA-UPPER', 'DUNA', 'basin.duna_upper'),
    ('DUNA-MIDDLE', 'DUNA', 'basin.duna_middle'),
    ('DUNA-LOWER', 'DUNA', 'basin.duna_lower'),
    ('BALATON', 'BALATON', 'basin.balaton')
) AS v(code, waterway_code, name_key)
JOIN waterway w ON w.code = v.waterway_code;

-- A `basin_i18n`-nek NINCS description oszlopa (a 02-es terv 5.3)
INSERT INTO basin_i18n (basin_id, lang, name)
SELECT b.id, v.lang, v.name
FROM (VALUES
    ('DUNA-UPPER', 'hu', 'Dunakulcs'),
    ('DUNA-UPPER', 'en', 'Upper Danube'),
    ('DUNA-MIDDLE', 'hu', 'Duna-kozep'),
    ('DUNA-MIDDLE', 'en', 'Middle Danube'),
    ('DUNA-LOWER', 'hu', 'Dunakozsog'),
    ('DUNA-LOWER', 'en', 'Lower Danube'),
    ('BALATON', 'hu', 'Balatoni medence'),
    ('BALATON', 'en', 'Lake Balaton basin')
) AS v(code, lang, name)
JOIN basin b ON b.code = v.code;

-- A teherfajtak (a `cargo_type` — a hajok rakomanya)
INSERT INTO cargo_type (code, nst_code, adn_code, imdg_code, is_bulk, is_container)
VALUES ('GENERAL', 'GENERAL', NULL, NULL, false, false),
       ('BULK', 'BULK', NULL, NULL, true, false),
       ('LIQUID', 'LIQUID', NULL, NULL, true, false),
       ('CONTAINER', 'CONTAINER', NULL, NULL, false, true),
       ('RO_RO', 'RO_RO', NULL, NULL, false, false),
       ('PASSENGER', NULL, NULL, NULL, false, false),
       ('EMPTY', NULL, NULL, NULL, false, false),
       ('MIXED', 'MIXED', NULL, NULL, true, false);

INSERT INTO cargo_type_i18n (cargo_type_code, lang, name, description)
VALUES ('GENERAL', 'hu', 'Altalanos teher', NULL),
       ('GENERAL', 'en', 'General cargo', NULL),
       ('BULK', 'hu', 'Szaraz teher', NULL),
       ('LIQUID', 'hu', 'Folyadek', NULL),
       ('CONTAINER', 'hu', 'Kontener', NULL),
       ('RO_RO', 'hu', 'Ro-ro', NULL),
       ('PASSENGER', 'hu', 'Utas', NULL),
       ('EMPTY', 'hu', 'Ures', NULL),
       ('MIXED', 'hu', 'Vegyes', NULL);

-- Az uzemeltetok (a `operator` — a hajok uzemeltetoi)
INSERT INTO operator (legal_name, country_code, website, founded)
VALUES ('Magyarorszagi Allami Hajozasi Tarsasag', 'HU', 'https://mahab.hu', 1946),
       ('Budapesti Hahozasi Zartkoruen', 'HU', NULL, 1850),
       ('Fonyodi Hahozati Zartkoruen', 'HU', NULL, 1969),
       ('Balatoni Hahozati Zartkoruen', 'HU', NULL, 1970),
       ('Hajozasi Szolgaltatok', 'HU', NULL, NULL);

-- Az uzemeltetonek nincs stabil kulcs-oszlopa -> a nevet hasznaljuk
-- az i18n-tablaban a `legal_name` alapjan (a 03-as terv szerint a
-- `operator` a `vessel.operator_id`-re mutat, nem a kodra).
-- Az `operator_i18n` oszlopa `display_name` (nem `name`) — a 02-es
-- terv 5.3 szerint az üzemeltetőnek nincs külön "neve", csak a
-- megjelenített neve.
INSERT INTO operator_i18n (operator_id, lang, display_name, description)
SELECT o.id, v.lang, v.name, NULL
FROM (VALUES
    ('Magyarorszagi Allami Hajozasi Tarsasag', 'hu', 'MAHAB'),
    ('Magyarorszagi Allami Hajozasi Tarsasag', 'en', 'MAHAB'),
    ('Budapesti Hahozasi Zartkoruen', 'hu', 'BAH'),
    ('Fonyodi Hahozati Zartkoruen', 'hu', 'Fonyodi Hahozati Zrt.'),
    ('Balatoni Hahozati Zartkoruen', 'hu', 'Balatoni Hahozati Zrt.'),
    ('Hajozasi Szolgaltatok', 'hu', 'Hajozasi Szolgaltatok')
) AS v(legal_name, lang, name)
JOIN operator o ON o.legal_name = v.legal_name;

-- =====================================================================

-- A hajótípus-kódok referenciatáblája (a seed).
--
-- Az `ais_type_code` a **nemzetközi AIS típuskód** (a SOLAS 1–99 és
-- a belvízi UNECE-ERI 8000–8519). A mérés (2026-11-22, a bud01
-- vevő) **15-féle** kódot mutatott:
--
--   8444 (15 hajó)  8443 (14)  8440 (11)  8000 (8)  60 (8)  69 (7)
--   80 (3)  8450 (3)  0 (1)  90 (1)  51 (2)  8430 (1)  8460 (1)
--   8220 (1)  + 2 null
--
-- A 8xxx-as sorozat a **belvízi (ERI) kódrendszer** — az UNECE
-- SC.3/WP.3 egyezmény és a CESNI ITU-R M.1371 kiegészítése; az
-- 1–99-es a SOLAS (nemzetközi) kódok.
--
-- A magyar nevek a `vessel_type_i18n` táblába mennek (a `lang='hu'`).
--
-- FORRÁS: ECE/TRANS/SC.3/WP.3/2020/22 (az UN–IMO hajótípus-
-- megfeleltetés) + a CESNI L_dir_syst_auto_ident_en_1.pdf.
--
-- **A `vessel.vessel_type_code` FK-ja erre mutat** — a seed nelkul
-- az ingest (a hajotipus kitoltes) elhalna.

INSERT INTO vessel_type
    (code, ais_type_code, cargo_category, is_self_propelled, operating_area)
VALUES
    ('UNKNOWN', NULL, NULL, true, 'duna'),
    ('ERI_8000', 8000, NULL, true, 'duna'),
    ('ERI_8010', 8010, 'general', true, 'duna'),
    ('ERI_8020', 8020, 'liquid', true, 'duna'),
    ('ERI_8021', 8021, 'liquid', true, 'duna'),
    ('ERI_8022', 8022, 'liquid', true, 'duna'),
    ('ERI_8023', 8023, 'dry', true, 'duna'),
    ('ERI_8030', 8030, 'container', true, 'duna'),
    ('ERI_8040', 8040, 'gas', true, 'duna'),
    ('ERI_8050', 8050, 'general', true, 'duna'),
    ('ERI_8060', 8060, 'liquid', true, 'duna'),
    ('ERI_8070', 8070, 'general', true, 'duna'),
    ('ERI_8080', 8080, 'mixed', true, 'duna'),
    ('ERI_8090', 8090, 'general', true, 'duna'),
    ('ERI_8100', 8100, 'mixed', true, 'duna'),
    ('ERI_8110', 8110, 'general', true, 'duna'),
    ('ERI_8120', 8120, 'liquid', true, 'duna'),
    ('ERI_8130', 8130, 'general', false, 'duna'),
    ('ERI_8140', 8140, 'mixed', false, 'duna'),
    ('ERI_8150', 8150, 'general', false, 'duna'),
    ('ERI_8160', 8160, 'liquid', false, 'duna'),
    ('ERI_8161', 8161, 'liquid', false, 'duna'),
    ('ERI_8162', 8162, 'liquid', false, 'duna'),
    ('ERI_8163', 8163, 'dry', false, 'duna'),
    ('ERI_8170', 8170, 'container', false, 'duna'),
    ('ERI_8180', 8180, 'gas', false, 'duna'),
    ('ERI_8210', 8210, 'general', true, 'duna'),
    ('ERI_8220', 8220, 'general', true, 'duna'),
    ('ERI_8230', 8230, 'general', true, 'duna'),
    ('ERI_8240', 8240, 'general', true, 'duna'),
    ('ERI_8250', 8250, 'general', true, 'duna'),
    ('ERI_8260', 8260, 'general', true, 'duna'),
    ('ERI_8270', 8270, 'general', true, 'duna'),
    ('ERI_8280', 8280, 'general', true, 'duna'),
    ('ERI_8290', 8290, 'general', true, 'duna'),
    ('ERI_8310', 8310, 'liquid', true, 'duna'),
    ('ERI_8320', 8320, 'liquid', true, 'duna'),
    ('ERI_8330', 8330, 'liquid', true, 'duna'),
    ('ERI_8340', 8340, 'liquid', true, 'duna'),
    ('ERI_8350', 8350, 'liquid', true, 'duna'),
    ('ERI_8360', 8360, 'liquid', true, 'duna'),
    ('ERI_8370', 8370, 'liquid', true, 'duna'),
    ('ERI_8380', 8380, 'liquid', true, 'duna'),
    ('ERI_8390', 8390, 'liquid', true, 'duna'),
    ('ERI_8400', 8400, NULL, true, 'duna'),
    ('ERI_8410', 8410, NULL, true, 'duna'),
    ('ERI_8420', 8420, NULL, true, 'duna'),
    ('ERI_8430', 8430, NULL, true, 'duna'),
    ('ERI_8440', 8440, 'passenger', true, 'duna'),
    ('ERI_8441', 8441, 'passenger', true, 'duna'),
    ('ERI_8442', 8442, 'passenger', true, 'duna'),
    ('ERI_8443', 8443, 'passenger', true, 'duna'),
    ('ERI_8444', 8444, 'passenger', true, 'duna'),
    ('ERI_8445', 8445, 'passenger', true, 'duna'),
    ('ERI_8446', 8446, 'passenger', true, 'duna'),
    ('ERI_8447', 8447, 'passenger', true, 'duna'),
    ('ERI_8448', 8448, 'passenger', true, 'duna'),
    ('ERI_8450', 8450, 'service', true, 'duna'),
    ('ERI_8451', 8451, 'service', true, 'duna'),
    ('ERI_8452', 8452, 'service', true, 'duna'),
    ('ERI_8453', 8453, 'service', true, 'duna'),
    ('ERI_8454', 8454, 'service', true, 'duna'),
    ('ERI_8460', 8460, 'service', true, 'duna'),
    ('ERI_8470', 8470, NULL, false, 'duna'),
    ('ERI_8480', 8480, NULL, true, 'duna'),
    ('ERI_8490', 8490, 'liquid', true, 'duna'),
    ('ERI_8500', 8500, 'liquid', false, 'duna'),
    ('ERI_8510', 8510, NULL, false, 'duna'),
    ('SOLAS_30', 30, 'fishing', true, 'duna'),
    ('SOLAS_33', 33, 'service', true, 'duna'),
    ('SOLAS_31', 31, 'towing', true, 'duna'),
    ('SOLAS_35', 35, 'military', true, 'duna'),
    ('SOLAS_36', 36, 'passenger', true, 'duna'),
    ('SOLAS_37', 37, 'passenger', true, 'duna'),
    ('SOLAS_40', 40, 'general', true, 'duna'),
    ('SOLAS_41', 41, 'container', true, 'duna'),
    ('SOLAS_42', 42, 'liquid', true, 'duna'),
    ('SOLAS_43', 43, 'container', true, 'duna'),
    ('SOLAS_44', 44, 'container', true, 'duna'),
    ('SOLAS_45', 45, 'general', true, 'duna'),
    ('SOLAS_50', 50, 'service', true, 'duna'),
    ('SOLAS_51', 51, 'service', true, 'duna'),
    ('SOLAS_52', 52, 'general', true, 'duna'),
    ('SOLAS_53', 53, 'passenger', true, 'duna'),
    ('SOLAS_55', 55, 'service', true, 'duna'),
    ('SOLAS_58', 58, 'passenger', true, 'duna'),
    ('SOLAS_60', 60, 'passenger', true, 'duna'),
    ('SOLAS_70', 70, 'general', true, 'duna'),
    ('SOLAS_79', 79, 'general', true, 'duna'),
    ('SOLAS_80', 80, 'liquid', true, 'duna'),
    ('SOLAS_89', 89, 'liquid', true, 'duna'),
    ('SOLAS_90', 90, NULL, true, 'duna'),
    ('SOLAS_99', 99, NULL, true, 'duna');

-- A magyar nevek (a `vessel_type_i18n`, a lang='hu')
INSERT INTO vessel_type_i18n (vessel_type_code, lang, name, description)
VALUES
    ('UNKNOWN', 'hu', 'ismeretlen típus', NULL),
    ('ERI_8000', 'hu', 'a hajó típusa ismeretlen (belvízi)', NULL),
    ('ERI_8010', 'hu', 'motoros teherhajó', NULL),
    ('ERI_8020', 'hu', 'motoros tanker', NULL),
    ('ERI_8021', 'hu', 'motoros tanker, folyadék, N-típus', NULL),
    ('ERI_8022', 'hu', 'motoros tanker, folyadék, C-típus', NULL),
    ('ERI_8023', 'hu', 'motoros tanker, száraz teher, folyadékként', NULL),
    ('ERI_8030', 'hu', 'konténerhajó', NULL),
    ('ERI_8040', 'hu', 'gáztanker', NULL),
    ('ERI_8050', 'hu', 'motoros teherhajó, vontató', NULL),
    ('ERI_8060', 'hu', 'motoros tanker, vontató', NULL),
    ('ERI_8070', 'hu', 'motoros teherhajó, egy vagy több mellette', NULL),
    ('ERI_8080', 'hu', 'motoros teherhajó tankhajóval', NULL),
    ('ERI_8090', 'hu', 'motoros teherhajó, egy vagy több teherhajót tol', NULL),
    ('ERI_8100', 'hu', 'motoros teherhajó, legalább egy tankhajót tol', NULL),
    ('ERI_8110', 'hu', 'vontató teherhajó', NULL),
    ('ERI_8120', 'hu', 'vontató tanker', NULL),
    ('ERI_8130', 'hu', 'vontató teherhajó, csatolt', NULL),
    ('ERI_8140', 'hu', 'vontató teherhajó/tanker, csatolt', NULL),
    ('ERI_8150', 'hu', 'teherbárka', NULL),
    ('ERI_8160', 'hu', 'tankbárka', NULL),
    ('ERI_8161', 'hu', 'tankbárka, folyadék, N-típus', NULL),
    ('ERI_8162', 'hu', 'tankbárka, folyadék, C-típus', NULL),
    ('ERI_8163', 'hu', 'tankbárka, száraz teher, folyadékként', NULL),
    ('ERI_8170', 'hu', 'teherbárka konténerekkel', NULL),
    ('ERI_8180', 'hu', 'gáztankbárka', NULL),
    ('ERI_8210', 'hu', 'tolóhajó, egy teherbárka', NULL),
    ('ERI_8220', 'hu', 'tolóhajó, két teherbárka', NULL),
    ('ERI_8230', 'hu', 'tolóhajó, három teherbárka', NULL),
    ('ERI_8240', 'hu', 'tolóhajó, négy teherbárka', NULL),
    ('ERI_8250', 'hu', 'tolóhajó, öt teherbárka', NULL),
    ('ERI_8260', 'hu', 'tolóhajó, hat teherbárka', NULL),
    ('ERI_8270', 'hu', 'tolóhajó, hét teherbárka', NULL),
    ('ERI_8280', 'hu', 'tolóhajó, nyolc teherbárka', NULL),
    ('ERI_8290', 'hu', 'tolóhajó, kilenc vagy több bárka', NULL),
    ('ERI_8310', 'hu', 'tolóhajó, egy tank-/gázbárka', NULL),
    ('ERI_8320', 'hu', 'tolóhajó, legalább két tank-/gázbárka', NULL),
    ('ERI_8330', 'hu', 'tolóhajó, legalább három tank-/gázbárka', NULL),
    ('ERI_8340', 'hu', 'tolóhajó, legalább négy tank-/gázbárka', NULL),
    ('ERI_8350', 'hu', 'tolóhajó, legalább öt tank-/gázbárka', NULL),
    ('ERI_8360', 'hu', 'tolóhajó, legalább hat tank-/gázbárka', NULL),
    ('ERI_8370', 'hu', 'tolóhajó, legalább hét tank-/gázbárka', NULL),
    ('ERI_8380', 'hu', 'tolóhajó, legalább nyolc tank-/gázbárka', NULL),
    ('ERI_8390', 'hu', 'tolóhajó, legalább kilenc tank-/gázbárka', NULL),
    ('ERI_8400', 'hu', 'vontató, egy', NULL),
    ('ERI_8410', 'hu', 'vontató, egy vagy több vontatás', NULL),
    ('ERI_8420', 'hu', 'vontató, segéd', NULL),
    ('ERI_8430', 'hu', 'tolóhajó, egy', NULL),
    ('ERI_8440', 'hu', 'személyhajó, komp, vöröskeresztes hajó', NULL),
    ('ERI_8441', 'hu', 'komp', NULL),
    ('ERI_8442', 'hu', 'vöröskeresztes hajó', NULL),
    ('ERI_8443', 'hu', 'Cruzehajó', NULL),
    ('ERI_8444', 'hu', 'személyhajó szállás nélkül', NULL),
    ('ERI_8445', 'hu', 'egynapos gyorsjáratú hajó', NULL),
    ('ERI_8446', 'hu', 'egynapos hidrofoil', NULL),
    ('ERI_8447', 'hu', 'vitorlázó Cruzehajó', NULL),
    ('ERI_8448', 'hu', 'vitorlázó személyhajó szállás nélkül', NULL),
    ('ERI_8450', 'hu', 'kisegítő hajó, rendőrségi, kikötői szolgálat', NULL),
    ('ERI_8451', 'hu', 'kisegítő hajó', NULL),
    ('ERI_8452', 'hu', 'rendőrségi járőrhajó', NULL),
    ('ERI_8453', 'hu', 'kikötői szolgálati hajó', NULL),
    ('ERI_8454', 'hu', 'navigációs felügyeleti hajó', NULL),
    ('ERI_8460', 'hu', 'munkahajó, karbantartó, úszó daru, kábelhajó, bójahajó, zsombor', NULL),
    ('ERI_8470', 'hu', 'vontatott tárgy, egyéb', NULL),
    ('ERI_8480', 'hu', 'halászhajó', NULL),
    ('ERI_8490', 'hu', 'bunkerhajó', NULL),
    ('ERI_8500', 'hu', 'bárka, tanker, vegyi', NULL),
    ('ERI_8510', 'hu', 'tárgy, egyéb', NULL),
    ('SOLAS_30', 'hu', 'halászhajó', NULL),
    ('SOLAS_31', 'hu', 'halászhajó (túzhalog)', NULL),
    ('SOLAS_33', 'hu', 'sócsaró', NULL),
    ('SOLAS_35', 'hu', 'katonai hajó', NULL),
    ('SOLAS_36', 'hu', 'sétáló', NULL),
    ('SOLAS_37', 'hu', 'kis vitorlázó', NULL),
    ('SOLAS_40', 'hu', 'nagyhajó', NULL),
    ('SOLAS_41', 'hu', 'konténerhajó', NULL),
    ('SOLAS_42', 'hu', 'tanker', NULL),
    ('SOLAS_43', 'hu', 'konténer/ro-ro', NULL),
    ('SOLAS_44', 'hu', 'ro-ro (konténer)', NULL),
    ('SOLAS_45', 'hu', 'ro-ro', NULL),
    ('SOLAS_50', 'hu', 'pilótahajó', NULL),
    ('SOLAS_51', 'hu', 'tengeri mentő', NULL),
    ('SOLAS_52', 'hu', 'hulladékszállító', NULL),
    ('SOLAS_53', 'hu', 'kórházhajó', NULL),
    ('SOLAS_55', 'hu', 'joghajó', NULL),
    ('SOLAS_58', 'hu', 'személyszállító hajó', NULL),
    ('SOLAS_60', 'hu', 'utasszállító hajó', NULL),
    ('SOLAS_70', 'hu', 'teherhajó', NULL),
    ('SOLAS_79', 'hu', 'teherhajó (további információ nélkül)', NULL),
    ('SOLAS_80', 'hu', 'tankhajó', NULL),
    ('SOLAS_89', 'hu', 'tanker (további információ nélkül)', NULL),
    ('SOLAS_90', 'hu', 'egyéb hajó', NULL),
    ('SOLAS_99', 'hu', 'egyéb hajó (további információ nélkül)', NULL);
