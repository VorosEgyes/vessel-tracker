"""A service réteg (a 03 §5.1: a router nem ír SQL-t).

**A lánc:** `router` -> `service` -> `repository` -> `DB`.

**A service tartja az üzleti logikát:**
- a `vessel_service.py`: a hajók lekérdezése + a write-oldal
  (a `sort_name` normalizált betöltése, a `slug` generálás);
- a `search_service.py`: a globális kereső (a F-SRCH-01…07);
- a `content_service.py`: a fordítás-fallback-lánc (a 03 §6.3);
- az `origin_service.py`: a mezőnkénti eredet összeállítása (a F-DET-15).
"""
