"""A domain réteg — a tiszta üzleti logika (a 01 – stack-terv §4.2).

**A szabály:** a `domain/` alatt **nincs** DB-hozzáférés, nincs HTTP,
nincs FastAPI — **csak tiszta függvények.** Így unit tesztelhető
(a 08 §2.1) és a coverage-kap alá esik (a 08 §8.1: a domain 90%).

**A mostani modul:** a `verification.py` — a bizonyossági szint
számítása (a F-DET-14, a F-CAT-14).
"""
