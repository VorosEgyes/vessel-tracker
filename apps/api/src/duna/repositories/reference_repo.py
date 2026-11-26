"""Queries for the public reference catalog."""

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

ReferenceKind = Literal[
    "ports",
    "locks",
    "waterways",
    "river-sections",
    "basins",
    "vessel-types",
    "operators",
    "routes",
    "cargo-types",
]


@dataclass(frozen=True)
class ReferenceQuery:
    table: str
    key: str
    columns: str
    translation_table: str
    translation_key: str
    name_column: str = "name"
    fallback_column: str = "code"


QUERIES: dict[ReferenceKind, ReferenceQuery] = {
    "ports": ReferenceQuery(
        "port",
        "id",
        "id, code, unlocode, port_type, waterway_id, country_code, river_km, is_active",
        "port_i18n",
        "port_id",
    ),
    "locks": ReferenceQuery(
        "lock",
        "id",
        "id, code, port_id, chamber_count, chamber_length_m, chamber_width_m, max_draft_m, operator_id, avg_transit_min, river_km",
        "lock_i18n",
        "lock_id",
    ),
    "waterways": ReferenceQuery(
        "waterway",
        "id",
        "id, code, waterway_type, length_km, is_active",
        "waterway_i18n",
        "waterway_id",
    ),
    "river-sections": ReferenceQuery(
        "river_section",
        "id",
        "id, code, waterway_id, country_code, km_from, km_to, risk_level, max_draft_m, fairway_code",
        "river_section_i18n",
        "river_section_id",
    ),
    "basins": ReferenceQuery("basin", "id", "id, code, waterway_id", "basin_i18n", "basin_id"),
    "vessel-types": ReferenceQuery(
        "vessel_type",
        "code",
        "code, un_code_28, ais_type_code, cargo_category, is_self_propelled, operating_area",
        "vessel_type_i18n",
        "vessel_type_code",
    ),
    "operators": ReferenceQuery(
        "operator",
        "id",
        "id, legal_name, country_code, website, founded",
        "operator_i18n",
        "operator_id",
        "display_name",
        "legal_name",
    ),
    "routes": ReferenceQuery(
        "route",
        "id",
        "id, code, origin_port_id, dest_port_id, distance_km, typical_duration_h, cargo_types",
        "route_i18n",
        "route_id",
    ),
    "cargo-types": ReferenceQuery(
        "cargo_type",
        "code",
        "code, nst_code, adn_code, imdg_code, is_bulk, is_container",
        "cargo_type_i18n",
        "cargo_type_code",
    ),
}


def _base_query(kind: ReferenceKind) -> str:
    spec = QUERIES[kind]
    # Identifiers here come exclusively from the static QUERIES map.
    translation = (
        f"SELECT t.{spec.name_column} FROM {spec.translation_table} t "
        f"WHERE t.{spec.translation_key} = r.{spec.key} AND t.{spec.name_column} IS NOT NULL "
        "AND t.lang IN (:lang, 'en', 'hu') "
        "ORDER BY CASE WHEN t.lang = :lang THEN 0 WHEN t.lang = 'en' THEN 1 ELSE 2 END "
        "LIMIT 1"
    )
    language = translation.replace(f"SELECT t.{spec.name_column}", "SELECT t.lang", 1)
    columns = ", ".join(f"r.{col.strip()}" for col in spec.columns.split(","))
    return (
        f"SELECT {columns}, COALESCE(({translation}), r.{spec.fallback_column}) AS name, "
        f"({language}) AS name_language FROM {spec.table} r"
    )


async def list_reference(
    session: AsyncSession,
    kind: ReferenceKind,
    lang: str,
    page: int,
    per_page: int,
    *,
    filters: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    filters = filters or {}
    allowed = {"waterway_id", "port_type", "country_code", "q"} if kind == "ports" else set()
    if set(filters) - allowed:
        raise ValueError("Unsupported reference filters")
    clauses = [
        f"r.{key} = :{key}"
        for key in ("waterway_id", "port_type", "country_code")
        if key in filters
    ]
    if "q" in filters:
        clauses.append(
            "(lower(r.code) LIKE :q ESCAPE '!' OR lower(COALESCE(r.unlocode, '')) LIKE :q ESCAPE '!'"
            " OR EXISTS (SELECT 1 FROM port_i18n p WHERE p.port_id = r.id"
            " AND lower(p.name) LIKE :q ESCAPE '!'))"
        )
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    params = dict(filters, lang=lang, limit=per_page, offset=(page - 1) * per_page)
    if "q" in filters:
        value = (
            str(filters["q"])
            .strip()
            .lower()
            .replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_")
        )
        params["q"] = f"%{value}%"
    spec = QUERIES[kind]
    total = (
        await session.execute(text(f"SELECT count(*) FROM {spec.table} r{where}"), params)
    ).scalar_one()
    sql = f"{_base_query(kind)}{where} ORDER BY r.{spec.key} LIMIT :limit OFFSET :offset"
    rows = (await session.execute(text(sql), params)).mappings().all()
    items = [dict(row) for row in rows]
    for item in items:
        item["name_fallback"] = item["name_language"] != lang
    if kind == "routes" and items:
        statement = text(
            "SELECT route_id, seq, port_id, typical_offset_h FROM route_stop "
            "WHERE route_id IN :ids ORDER BY route_id, seq"
        ).bindparams(bindparam("ids", expanding=True))
        stops = (
            await session.execute(statement, {"ids": [item["id"] for item in items]})
        ).mappings()
        by_route: dict[int, list[dict[str, Any]]] = {item["id"]: [] for item in items}
        for stop in stops:
            by_route[stop["route_id"]].append(dict(stop))
        for item in items:
            item["stops"] = by_route[item["id"]]
    return items, total


async def get_reference(
    session: AsyncSession,
    kind: Literal["ports", "locks"],
    object_id: int,
    lang: str,
) -> dict[str, Any] | None:
    row = (
        (
            await session.execute(
                text(f"{_base_query(kind)} WHERE r.id = :id"), {"id": object_id, "lang": lang}
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    item = dict(row)
    item["name_fallback"] = item["name_language"] != lang
    if kind == "ports":
        for key, sql in {
            "berths": "SELECT id, code, length_m, depth_m, max_draft_m, unload_rate_t_h FROM berth WHERE port_id = :id ORDER BY id",
            "terminals": "SELECT id, operator_id, annual_capacity_t, storage_capacity_t, rail_access, gear_types FROM terminal WHERE port_id = :id ORDER BY id",
        }.items():
            item[key] = [
                dict(r) for r in (await session.execute(text(sql), {"id": object_id})).mappings()
            ]
        lock_sql = f"{_base_query('locks')} WHERE r.port_id = :id ORDER BY r.id"
        locks = (await session.execute(text(lock_sql), {"id": object_id, "lang": lang})).mappings()
        item["locks"] = [dict(r, name_fallback=r["name_language"] != lang) for r in locks]
    else:
        sql = "SELECT id, status, valid_from, valid_to, note, source FROM lock_status WHERE lock_id = :id ORDER BY valid_from DESC, id DESC"
        item["statuses"] = [
            dict(r) for r in (await session.execute(text(sql), {"id": object_id})).mappings()
        ]
    return item
