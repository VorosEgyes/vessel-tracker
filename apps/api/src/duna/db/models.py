"""Az ORM modellek (a SQLAlchemy 2.0, a 01 §4.2).

**A `03` szerint a modellek a DB-sémából generálódnak** (a
`datamodel-code-generator`) → **egyelőre kézzel vannak megírva**
(a `03` §5.1a: "a `response_model` NEM kézzel írt másolat — a
DB-sémából generálódik") → **a `just ddl-diff` (a `02` §11) a
séma-driftet ellenőrzi** → **a modellek kézi karbantartása a
generálás bevezetéséig elfogadható.**

**Az itt definiált táblák (a `02` §5.1):** a `language`, a
`vessel_type`, a `vessel`, a `vessel_i18n`, a `operator`,
a `operator_i18n` → **a katalóguslista (a `03` §3.1
`GET /api/v1/vessels`) ezeket használja.**
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """A deklaratív alap (a SQLAlchemy 2.0)."""


class Language(Base):
    """A nyelv (a `02` §5.1)."""

    __tablename__ = "language"

    code: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    name_native: Mapped[str] = mapped_column(String)
    name_en: Mapped[str] = mapped_column(String)
    is_rtl: Mapped[bool] = mapped_column(Boolean, default=False)


class VesselType(Base):
    """A hajótípus (a `02` §5.1)."""

    __tablename__ = "vessel_type"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    un_code_28: Mapped[str | None] = mapped_column(String, nullable=True)
    ais_type_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    cargo_category: Mapped[str | None] = mapped_column(String, nullable=True)
    is_self_propelled: Mapped[bool] = mapped_column(Boolean, default=True)
    operating_area: Mapped[str] = mapped_column(String, default="duna")


class VesselTypeI18n(Base):
    """A hajótípus neve (a `02` §5.1) — fordított."""

    __tablename__ = "vessel_type_i18n"

    vessel_type_code: Mapped[str] = mapped_column(
        String, ForeignKey("vessel_type.code"), primary_key=True
    )
    lang: Mapped[str] = mapped_column(CHAR(2), ForeignKey("language.code"), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


class Operator(Base):
    """Az üzemeltető (a `02` §5.1)."""

    __tablename__ = "operator"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class OperatorI18n(Base):
    """Az üzemeltető neve (a `02` §5.1)."""

    __tablename__ = "operator_i18n"

    operator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operator.id", ondelete="CASCADE"), primary_key=True
    )
    lang: Mapped[str] = mapped_column(CHAR(2), ForeignKey("language.code"), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


class Country(Base):
    """Az ország (a `02` §5.1) — a `flag_country_code` hivatkozik rá."""

    __tablename__ = "country"

    code: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    name: Mapped[str] = mapped_column(String)


class Port(Base):
    """A kikötő (a `02` §5.1) — a `home_port_id` hivatkozik rá."""

    __tablename__ = "port"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    operating_area: Mapped[str] = mapped_column(String, default="duna")


class VesselIdentifier(Base):
    """A hajó azonosítója (a `02` §5.1).

    **A `valid_to IS NULL` az AKTÍV** (a 03 §3.1: a `/aliases` a
    lezártakat adja, a `/identifiers` mindet).
    """

    __tablename__ = "vessel_identifier"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    vessel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vessel.id", ondelete="CASCADE"))
    identifier_type: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[str] = mapped_column(String)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class Vessel(Base):
    """A hajó (a `02` §5.1).

    **A `verification_level` a TÁROLT érték** (a `03` §3.1: a szűrő
    a tárolt értékre épül) → **az adatlap a számítottat adja** (a
    `vessel_verification` nézet, a `02` §6.2).
    """

    __tablename__ = "vessel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mmsi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eni: Mapped[str | None] = mapped_column(CHAR(8), nullable=True)
    imo: Mapped[str | None] = mapped_column(CHAR(7), nullable=True)
    callsign: Mapped[str | None] = mapped_column(String, nullable=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    sort_name: Mapped[str] = mapped_column(String, default="")
    vessel_type_code: Mapped[str] = mapped_column(String, ForeignKey("vessel_type.code"))
    operating_area: Mapped[str] = mapped_column(String, default="duna")
    flag_country_code: Mapped[str] = mapped_column(CHAR(2), ForeignKey("country.code"))
    operator_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("operator.id"), nullable=True
    )
    home_port_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("port.id"), nullable=True
    )
    destination: Mapped[str | None] = mapped_column(String, nullable=True)
    build_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    length_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    beam_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    draught_max_m: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    gross_tonnage: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    deadweight_t: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    teu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_kw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ais_class: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    verification_level: Mapped[str] = mapped_column(String, default="name_only")
    is_passenger_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    passenger_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # **a kapcsolatok** (a `03` §5.4: a JOIN-ek a service/repo rétegen)
    type: Mapped[VesselType] = relationship(lazy="joined")
    operator: Mapped[Operator | None] = relationship(lazy="joined")
    names: Mapped[list[VesselI18n]] = relationship(lazy="selectin", back_populates="vessel")


class VesselI18n(Base):
    """A hajó neve (a `02` §5.1).

    **A `name` a hivatalos latin név** (nem fordul, a §5.8.4) → **a
    `sort_name` a rendezéshez** (a `vessel`-en, denormalizálva).
    """

    __tablename__ = "vessel_i18n"

    vessel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vessel.id", ondelete="CASCADE"), primary_key=True
    )
    lang: Mapped[str] = mapped_column(CHAR(2), ForeignKey("language.code"), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    vessel: Mapped[Vessel] = relationship(back_populates="names")
