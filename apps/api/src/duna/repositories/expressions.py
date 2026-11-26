"""Shared expressions for localized vessel data."""

from sqlalchemy import case, select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement

from duna.db.models import (
    OperatorI18n,
    PortI18n,
    Vessel,
    VesselI18n,
    VesselIdentifier,
    VesselTypeI18n,
)


def _language_order(lang: str, column: InstrumentedAttribute[str]) -> ColumnElement[int]:
    return case((column == lang, 0), (column == "en", 1), (column == "hu", 2), else_=3)


def vessel_name(lang: str) -> ColumnElement[str]:
    return (
        select(VesselI18n.name)
        .where(VesselI18n.vessel_id == Vessel.id)
        .order_by(_language_order(lang, VesselI18n.lang), VesselI18n.lang)
        .limit(1)
        .correlate(Vessel)
        .scalar_subquery()
    )


def vessel_type_name(lang: str) -> ColumnElement[str]:
    return (
        select(VesselTypeI18n.name)
        .where(VesselTypeI18n.vessel_type_code == Vessel.vessel_type_code)
        .order_by(_language_order(lang, VesselTypeI18n.lang), VesselTypeI18n.lang)
        .limit(1)
        .correlate(Vessel)
        .scalar_subquery()
    )


def operator_name(lang: str) -> ColumnElement[str]:
    return (
        select(OperatorI18n.display_name)
        .where(
            OperatorI18n.operator_id == Vessel.operator_id, OperatorI18n.display_name.is_not(None)
        )
        .order_by(_language_order(lang, OperatorI18n.lang), OperatorI18n.lang)
        .limit(1)
        .correlate(Vessel)
        .scalar_subquery()
    )


def port_name(lang: str) -> ColumnElement[str]:
    return (
        select(PortI18n.name)
        .where(PortI18n.port_id == Vessel.home_port_id)
        .order_by(_language_order(lang, PortI18n.lang), PortI18n.lang)
        .limit(1)
        .correlate(Vessel)
        .scalar_subquery()
    )


def display_identifier_id() -> ColumnElement[int]:
    preferred = case(
        (Vessel.operating_area == "duna", "eni"),
        else_="national_reg_no",
    )
    return (
        select(VesselIdentifier.id)
        .where(VesselIdentifier.vessel_id == Vessel.id, VesselIdentifier.valid_to.is_(None))
        .order_by(
            (VesselIdentifier.identifier_type == preferred).desc(),
            VesselIdentifier.is_primary.desc(),
            VesselIdentifier.id,
        )
        .limit(1)
        .correlate(Vessel)
        .scalar_subquery()
    )
