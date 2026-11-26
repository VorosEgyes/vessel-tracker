"""A mezőnkénti eredet összeállítása (a 03 §5.1 — a F-DET-15).

**A `vessel_data_origin` a konfliktust mutatja:** két forrás, két
különböző érték → **a `value_snapshot` az adott forrástól
származó érték** (a `prof` reviewer C-3 findingje) → **a konfliktus
csak ezzel látható.**
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from duna.repositories.vessel_sub_repo import list_data_origins
from duna.schemas.vessel import FieldOrigin


async def get_field_origins(session: AsyncSession, vessel_id: int) -> list[FieldOrigin]:
    """A mezőnkénti eredet (a F-DET-15).

    **Csak az aktuális források** (`is_current`) → **a történeti
    források a `vessel_data_origin`-ban maradnak, de nem jelennek meg.**
    """
    return await list_data_origins(session, vessel_id)


def group_by_field(origins: list[FieldOrigin]) -> dict[str, list[FieldOrigin]]:
    """A mezőnkénti eredet mezőnkénti csoportosítása.

    **A `conflicting_fields` a konfliktusos mezők listája** (ahol
    egynél több forrás van) → **a szerkesztői felület ezt jelzi**
    (a `06` §4.2).
    """
    grouped: dict[str, list[FieldOrigin]] = {}
    for origin in origins:
        grouped.setdefault(origin.field_name, []).append(origin)
    return grouped
