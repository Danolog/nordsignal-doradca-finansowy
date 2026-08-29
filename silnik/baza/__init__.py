# -*- coding: utf-8 -*-
"""Schemat bazy w dialekcie PostgreSQL — JEDEN punkt zlozenia.

DLACZEGO TO NIE JEST SAM PLIK `schemat.sql`. Pelny schemat ma CZTERNASCIE
tabel, a `schemat.sql` niesie trzynascie. Czternasta — `rejestr_stawek` —
mieszka w `wiedza/rejestr.py`, razem z regula "silnik czyta wylacznie stawki
zatwierdzone przez czlowieka" (CLAUDE.md §3.3/§3.4). Przepisanie jej do
`schemat.sql` byloby drugim nosnikiem liczb pochodzacych z ustaw.

Ktos, kto postawi baze z samego `schemat.sql`, dostanie baze, ktora WYGLADA
na kompletna: migracja przejdzie, tabele beda, a rejestr stawek nie bedzie
istnial i aplikacja nie policzy ani jednej kwoty. To jest ta klasa
przeoczenia, ktora daje "migracja przeszla, tylko rejestr pusty".

Zlozenie jest DOKLADNYM odpowiednikiem tego, co robi `magazyn.polacz()` po
stronie SQLite: `_SCHEMAT` + `rejestr.SCHEMAT_SQLITE`. Rownoleglosc obu
zlozen pilnuje `testy/test_schemat_dwa_dialekty.py`.
"""
from __future__ import annotations

import pathlib

PLIK_SCHEMATU = pathlib.Path(__file__).resolve().parent / "schemat.sql"


def schemat_postgresql() -> str:
    """Pelny napis DDL dla PostgreSQL — trzynascie tabel z pliku plus rejestr.

    Zwraca napis, nie wykonuje go. Wykonanie nalezy do kroku migracji, ktory
    jest osobna, swiadoma czynnoscia (W2/W4).
    """
    from wiedza import rejestr

    return (PLIK_SCHEMATU.read_text(encoding="utf-8")
            + "\n-- ── rejestr stawek: nosnik w `wiedza/rejestr.py` ──────────\n"
            + rejestr.SCHEMAT)
