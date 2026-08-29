# -*- coding: utf-8 -*-
"""Przyrzad pomiarowy do porownania dwoch nosnikow schematu bazy.

NIE JEST TESTEM. Jest narzedziem, ktorego uzywa
`testy/test_schemat_wobec_bazy.py`. Wydzielony, zeby straznik mowil o tym,
CO porownuje, a nie o tym, JAK czyta SQL.

CO TEN PARSER WIDZI — i tylko to wolno na niego powolywac:
  * nazwy tabel,
  * nazwy kolumn w tabeli,
  * typ kolumny (napis sprzed pierwszego slowa wiezu),
  * obowiazkowosc (`NOT NULL`, `PRIMARY KEY`, `SERIAL`),
  * wartosc domyslna (`DEFAULT ...`),
  * dziedzine wyliczeniowa kolumny (`CHECK (kolumna IN (...))`) — z wiezu
    przy kolumnie ORAZ z wiezu nazwanego na poziomie tabeli,
  * nazwy wiezow `CONSTRAINT`,
  * krotki `UNIQUE`,
  * nazwy indeksow zakladanych osobnym `CREATE INDEX`,
  * liczbe polecen `CREATE TABLE` liczona niezaleznie od parsowania
    (`ile_polecen_create_table`) — kontrola, ze parser niczego nie zgubil.

CZEGO NIE WIDZI — nazwane wprost, zeby nikt nie wzial ciszy za zgode:
  * tresci wiezu `CHECK` innego niz `IN (...)` (porownuje sie NAZWY, nie tresc),
  * kolumn indeksu i warunku `WHERE` w indeksie czesciowym (tylko nazwa),
  * `REFERENCES` i zachowania przy kasowaniu,
  * kolejnosci kolumn,
  * czegokolwiek, co powstaje `ALTER TABLE` juz po zalozeniu tabeli.

Parser jest swiadomie prostszy niz pelny SQL. Parser bogatszy niz napis,
ktory parsuje, sam zaczyna byc miejscem wady — ta sama zasada, co przy
`testy/test_rejestr_ddl.py::_kolumny_z_napisu`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Slowa, po ktorych konczy sie napis typu w definicji kolumny.
_SLOWA_WIEZOW = ("NOT NULL", "PRIMARY KEY", "UNIQUE", "DEFAULT", "REFERENCES",
                 "CHECK", "GENERATED")


@dataclass(frozen=True)
class Kolumna:
    nazwa: str
    typ: str
    obowiazkowa: bool
    domyslna: str | None
    dziedzina: tuple[str, ...] | None


@dataclass
class Tabela:
    nazwa: str
    kolumny: dict[str, Kolumna] = field(default_factory=dict)
    unikalne: set[tuple[str, ...]] = field(default_factory=set)
    wiezy: set[str] = field(default_factory=set)


def _bez_komentarzy(sql: str) -> str:
    return "\n".join(re.sub(r"--.*$", "", linia) for linia in sql.splitlines())


def _podziel_na_przecinkach_pierwszego_poziomu(cialo: str) -> list[str]:
    czesci: list[str] = []
    glebokosc = 0
    biezaca: list[str] = []
    for znak in cialo:
        if znak == "(":
            glebokosc += 1
        elif znak == ")":
            glebokosc -= 1
        if znak == "," and glebokosc == 0:
            czesci.append("".join(biezaca))
            biezaca = []
        else:
            biezaca.append(znak)
    if "".join(biezaca).strip():
        czesci.append("".join(biezaca))
    return [c.strip() for c in czesci if c.strip()]


def _ciala_tabel(sql: str) -> dict[str, str]:
    """Nazwa tabeli -> tresc miedzy nawiasami `CREATE TABLE`."""
    sql = _bez_komentarzy(sql)
    wynik: dict[str, str] = {}
    for m in re.finditer(
            r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-z_]+)\s*\(", sql,
            re.IGNORECASE):
        poczatek = m.end() - 1
        glebokosc = 0
        i = poczatek
        while i < len(sql):
            if sql[i] == "(":
                glebokosc += 1
            elif sql[i] == ")":
                glebokosc -= 1
                if glebokosc == 0:
                    break
            i += 1
        wynik[m.group(1)] = sql[poczatek + 1:i]
    return wynik


def _dziedzina(tekst: str) -> tuple[str, ...] | None:
    """Wartosci z `IN ('a','b')`, posortowane. `None`, gdy wiezu nie ma."""
    m = re.search(r"\bIN\s*\(([^)]*)\)", tekst, re.IGNORECASE)
    if not m:
        return None
    return tuple(sorted(w.strip().strip("'") for w in m.group(1).split(",")))


def parsuj(sql: str) -> dict[str, Tabela]:
    """Napis DDL -> mapa tabel. Dziala na obu dialektach."""
    tabele: dict[str, Tabela] = {}
    for nazwa_tabeli, cialo in _ciala_tabel(sql).items():
        tabela = Tabela(nazwa_tabeli)
        dziedziny_z_wiezow: dict[str, tuple[str, ...]] = {}
        for czesc in _podziel_na_przecinkach_pierwszego_poziomu(cialo):
            gora = " ".join(czesc.upper().split())
            if gora.startswith(("CONSTRAINT", "UNIQUE", "PRIMARY KEY", "CHECK",
                                "FOREIGN KEY")):
                if gora.startswith("UNIQUE"):
                    m = re.search(r"UNIQUE\s*\(([^)]*)\)", czesc, re.IGNORECASE)
                    if m:
                        tabela.unikalne.add(
                            tuple(sorted(k.strip() for k in m.group(1).split(","))))
                elif gora.startswith("CONSTRAINT"):
                    m = re.match(r"CONSTRAINT\s+([a-z_]+)\s+(.*)", czesc,
                                 re.IGNORECASE | re.DOTALL)
                    if m:
                        # `CONSTRAINT x UNIQUE (...)` — wiez jednoznacznosci
                        # Z NAZWA WLASNA. Do W4 parser go NIE WIDZIAL: caly
                        # `CONSTRAINT ...` szedl do zbioru nazw wiezow, wiec
                        # nazwanie istniejacego `UNIQUE` po cichu zabieralo
                        # go z porownania. Wyszlo to na jaw dopiero wtedy, gdy
                        # `numer_faktury` dostal nazwe wlasna (2026-08-29):
                        # napis niosl trzy wiezy, baza cztery.
                        mu = re.search(r"UNIQUE\s*\(([^)]*)\)", m.group(2),
                                       re.IGNORECASE)
                        if mu:
                            tabela.unikalne.add(tuple(sorted(
                                k.strip() for k in mu.group(1).split(","))))
                            continue
                        tabela.wiezy.add(m.group(1))
                        # `CHECK (kolumna IN (...))` — dziedzina przypisana
                        # do kolumny, zeby dalo sie ja porownac miedzy
                        # dialektami niezaleznie od nazwy wiezu.
                        mk = re.search(r"CHECK\s*\(\s*([a-z_]+)\s+IN\s*\(([^)]*)\)",
                                       m.group(2), re.IGNORECASE)
                        if mk:
                            dziedziny_z_wiezow[mk.group(1)] = tuple(sorted(
                                w.strip().strip("'") for w in mk.group(2).split(",")))
                continue

            m = re.match(r"([a-z_]+)\s+(.*)", czesc, re.DOTALL)
            if not m:
                continue
            nazwa_kolumny = m.group(1)
            reszta = " ".join(m.group(2).split())
            gora_reszty = reszta.upper()
            pozycje = [gora_reszty.find(s) for s in _SLOWA_WIEZOW
                       if gora_reszty.find(s) >= 0]
            typ = reszta[:min(pozycje)].strip() if pozycje else reszta.strip()
            dom = re.search(r"DEFAULT\s+('[^']*'|[A-Za-z0-9_.]+(?:\(\))?)",
                            reszta, re.IGNORECASE)
            tabela.kolumny[nazwa_kolumny] = Kolumna(
                nazwa=nazwa_kolumny,
                typ=typ,
                obowiazkowa=("NOT NULL" in gora_reszty
                             or "PRIMARY KEY" in gora_reszty
                             or "SERIAL" in typ.upper()),
                domyslna=dom.group(1) if dom else None,
                dziedzina=_dziedzina(reszta) if "CHECK" in gora_reszty else None,
            )
            if "UNIQUE" in gora_reszty:
                tabela.unikalne.add((nazwa_kolumny,))

        for kolumna, wartosci in dziedziny_z_wiezow.items():
            if kolumna in tabela.kolumny:
                stara = tabela.kolumny[kolumna]
                tabela.kolumny[kolumna] = Kolumna(
                    nazwa=stara.nazwa, typ=stara.typ,
                    obowiazkowa=stara.obowiazkowa, domyslna=stara.domyslna,
                    dziedzina=wartosci)
        tabele[nazwa_tabeli] = tabela
    return tabele


def indeksy(sql: str) -> set[str]:
    """Nazwy indeksow zakladanych osobnym `CREATE INDEX` / `CREATE UNIQUE INDEX`."""
    return set(re.findall(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-z_]+)",
        _bez_komentarzy(sql), re.IGNORECASE))


#: PostgreSQL zna typy, SQLite ich nie ma. Kazdy typ PostgreSQL nalezy do
#: RODZINY, a rodzina ma DOKLADNIE JEDEN dopuszczalny odpowiednik w SQLite.
#: `ZMIENNOPRZECINKOWA` nie ma odpowiednika swiadomie — CLAUDE.md §3.1 mowi,
#: ze liczba zmiennoprzecinkowa w sciezce kwoty jest wada krytyczna, wiec
#: straznik ma sie na niej zaczerwienic, a nie ja przetlumaczyc.
RODZINA_POSTGRESQL = {
    "NUMERIC": "kwota", "DECIMAL": "kwota",
    "DATE": "data",
    "TIMESTAMPTZ": "czas", "TIMESTAMP": "czas",
    "BOOLEAN": "flaga", "BOOL": "flaga",
    "BIGSERIAL": "calkowita", "SERIAL": "calkowita",
    "INT": "calkowita", "INTEGER": "calkowita", "BIGINT": "calkowita",
    "SMALLINT": "calkowita",
    "TEXT": "tekst", "VARCHAR": "tekst", "CHAR": "tekst",
    "REAL": "ZMIENNOPRZECINKOWA", "DOUBLE": "ZMIENNOPRZECINKOWA",
    "FLOAT": "ZMIENNOPRZECINKOWA",
}

#: Rodzina -> typ, ktory MUSI stac po stronie SQLite.
ODPOWIEDNIK_SQLITE = {
    "kwota": "TEXT",
    "data": "TEXT",
    "czas": "TEXT",
    "tekst": "TEXT",
    "flaga": "INTEGER",
    "calkowita": "INTEGER",
}


def rodzina(typ_postgresql: str) -> str:
    """Rodzina typu PostgreSQL. Typ nieznany zwraca sie z prefiksem `NIEZNANY:`."""
    rdzen = typ_postgresql.split("(")[0].split()[0].upper() if typ_postgresql else ""
    return RODZINA_POSTGRESQL.get(rdzen, f"NIEZNANY:{typ_postgresql}")


def typ_sqlite(kolumna: Kolumna) -> str:
    """Pierwsze slowo typu po stronie SQLite (`INTEGER PRIMARY KEY` -> `INTEGER`)."""
    return kolumna.typ.split()[0].upper() if kolumna.typ else ""


def porownaj_domyslna(a: str | None, b: str | None, *,
                      rodzina_kolumny: str) -> bool:
    """Czy wartosci domyslne znacza to samo w obu dialektach.

    `0`/`1` po stronie SQLite znaczy to, co `FALSE`/`TRUE` po stronie
    PostgreSQL — ale WYLACZNIE dla rodziny `flaga`. Tlumaczenie stosowane
    bez tego warunku bylo by za szerokie: `kolejnosc INT DEFAULT 0` po jednej
    stronie zgadzaloby sie z `BOOLEAN DEFAULT FALSE` po drugiej, czyli
    straznik przepuscilby zmiane typu kolumny licznikowej na logiczna.
    """
    def norma(w: str | None) -> str | None:
        if w is None:
            return None
        w = w.strip().strip("'").upper()
        if rodzina_kolumny == "flaga":
            return {"0": "FALSE", "1": "TRUE"}.get(w, w)
        return w

    return norma(a) == norma(b)


def ile_polecen_create_table(sql: str) -> int:
    """Ile `CREATE TABLE` niesie napis — liczone NIEZALEZNIE od `parsuj`.

    Kontrola dwustronna dla parsera: gdy `parsuj` zwroci mniej tabel niz ta
    liczba, znaczy to, ze napis urwal sie w polowie albo ze parser zgubil
    tabele — a nie, ze schemat sie zmienil. Parser sprawdzajacy sam siebie
    nie sprawdza niczego.
    """
    return len(re.findall(r"CREATE\s+TABLE", _bez_komentarzy(sql), re.IGNORECASE))


def dziedzina_z_bazy(definicja: str) -> tuple[str, ...] | None:
    """Dziedzina wyliczeniowa z odpowiedzi serwera na `pg_get_constraintdef`.

    DLACZEGO OSOBNA FUNKCJA. Serwer NIE oddaje wiezu w postaci, w ktorej go
    zapisalismy: `CHECK (typ IN ('a','b'))` wraca jako
    `CHECK ((typ = ANY (ARRAY['a'::text, 'b'::text])))`. Parser napisu DDL
    czyta nasz zapis, ten czyta zapis serwera — i to jest cala roznica miedzy
    „napis obiecuje" a „baza egzekwuje".
    """
    m = re.search(r"\(\s*([a-z_]+)\s*=\s*ANY\s*\(\s*ARRAY\[(.*?)\]",
                  definicja, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    wartosci = []
    for kawalek in m.group(2).split(","):
        w = kawalek.strip()
        if "::" in w:
            w = w.split("::")[0].strip()
        wartosci.append(w.strip().strip("'"))
    return tuple(sorted(wartosci))


def kolumna_wiezu_z_bazy(definicja: str) -> str | None:
    """Nazwa kolumny, ktorej dotyczy dziedzina z `pg_get_constraintdef`."""
    m = re.search(r"\(\s*([a-z_]+)\s*=\s*ANY\s*\(", definicja, re.IGNORECASE)
    return m.group(1) if m else None
