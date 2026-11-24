"""Az ingest réteg — az AIS parser és a pipeline (a 04 – parser-terv).

**A szabály:** a parser **tiszta függvények** → nincs DB, nincs
hálózat → unit és property tesztelhető (a `04` §10).

**A mostani modul:** a `decoder.py` — a 6 bites karakterkódolás és az
üzenetfejlécek (a `04` §4.1–§4.2).
"""
