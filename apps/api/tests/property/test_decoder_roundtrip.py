"""A 6 bites kódolás round-trip property tesztje (a `08` §4.2).

**A `04` §10 szerint ez a LEGFONTOSABB teszt:** „a 6 bites kódolás kézi
implementálásánál a legkisebb hiba is elcsúszik egy bittel" → **a
`hypothesis` generálja a véletlen biteket, és ellenőrzi, hogy a
dekódolás → visszaalakítás az eredetit adja.**

**Két kódolás (a 2026-11-24-i mérés):**
- a **standard AIS armor** (az ITU-R M.1371) → a `decode_standard_6bit`;
- a **vevő fizikai értékei** (a `bud01`) → **NEM round-trip
  tesztelhető** (a visszafejtés nem egyértelmű: a vevő egy inverz
  táblázattal alakít karakterré) → **a fizikai forma decode-only**.

**A `HYPOTHESIS_MAX_EXAMPLES` env-variábilis** korlátozza a példák
számát (a CI-ban 100, a nightlyban 10 000 — a `08` §4.2).
"""

import os

from hypothesis import given, settings
from hypothesis import strategies as st

from duna.ingest.decoder import (
    decode_standard_6bit,
    encode_standard_6bit,
)

# A CI-ban 100 pelda (a 08 §4.2) -> a nightlyban 10 000
MAX_EXAMPLES = int(os.environ.get("HYPOTHESIS_MAX_EXAMPLES", "100"))

# a standard armor karakterei
STANDARD_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@"


@settings(max_examples=MAX_EXAMPLES)
@given(st.text(alphabet=STANDARD_ALPHABET, min_size=1, max_size=62))
def test_a_standard_armor_roundtrip(payload: str) -> None:
    """A standard armor dekódolás → visszaalakítás az eredetit adja."""
    assert encode_standard_6bit(decode_standard_6bit(payload)) == payload


@settings(max_examples=MAX_EXAMPLES)
@given(st.lists(st.integers(min_value=0, max_value=62), min_size=1, max_size=62))
def test_a_standard_ertekek_visszaalakitas(values: list[int]) -> None:
    """A 6 bites értékek → karakterek → értékek: az eredeti."""
    assert decode_standard_6bit(encode_standard_6bit(values)) == values


@settings(max_examples=MAX_EXAMPLES)
@given(st.binary(min_size=1, max_size=62))
def test_a_bitek_sorszama_a_karakterek_szerint(payload: bytes) -> None:
    """A bitek száma mindig a karakterek száma × 6 (a `04` §3.3).

    **A `fill_bits` nélkül** — a kitöltő bitek levágása külön
    tesztelve van.
    """
    from duna.ingest.decoder import payload_to_bits

    text = payload.decode("latin-1")
    # a nem ASCII karaktereket kiszuresenuk (a standard armor hibat dob)
    text = "".join(ch for ch in text if ch in STANDARD_ALPHABET)
    if not text:
        return
    assert len(payload_to_bits(text)) == len(text) * 6
