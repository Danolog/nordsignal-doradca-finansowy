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

Zlozenie jest JEDYNYM nosnikiem schematu. Do W4 (2026-08-29) istnial drugi —
dialekt SQLite (`magazyn._SCHEMAT` + `rejestr.SCHEMAT_SQLITE`) — dopuszczony
jako swiadomy dlug z jawnym progiem „znika, gdy aplikacja przestanie otwierac
SQLite". Prog zadzialal; napisy skasowane. Pilnuje tego
`testy/test_schemat_wobec_bazy.py`, ktory porownuje ten napis z BAZA
POSTAWIONA Z NIEGO — a nie, jak jego poprzednik, dwa napisy ze soba.
"""
from __future__ import annotations

import pathlib
import re

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


def tabele_i_indeksy() -> tuple[str, str]:
    """Ten sam napis DDL, rozciety na `CREATE TABLE` i `CREATE INDEX`.

    DLACZEGO KOLEJNOSC MA ZNACZENIE — znalezisko W4, 2026-08-29. Indeks
    czesciowy `wpisy_do_rachunku` ma warunek na kolumnie `zrodlo`. W bazie,
    ktora JUZ ISTNIEJE bez tej kolumny, `CREATE TABLE IF NOT EXISTS` niczego
    nie dokłada — kolumne dopisuje dopiero `magazyn._dopisz_kolumny`. Napis
    wykonany w calosci probowal wiec zalozyc indeks na kolumnie, ktorej
    jeszcze nie ma, i CALA MIGRACJA padala. Baza swieza tego nie widzi, bo
    tam kolumna powstaje razem z tabela; wyszlo to na jaw dopiero na
    strazniku migracji ze schematu 11.

    Rozciecie idzie po TYM SAMYM napisie, nie po drugiej kopii — `schemat.sql`
    i `rejestr.SCHEMAT` zostaja jedynymi nosnikami.
    """
    napis = schemat_postgresql()
    granica = re.compile(r"^\s*CREATE\s+(?:UNIQUE\s+)?INDEX", re.M)
    tabele, indeksy = [], []
    for kawalek in napis.split(";"):
        (indeksy if granica.search(kawalek) else tabele).append(kawalek)
    return ";".join(tabele) + ";", ";".join(indeksy) + ";"
