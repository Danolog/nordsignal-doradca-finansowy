# -*- coding: utf-8 -*-
"""ZASILENIE POCZATKOWE REJESTRU — stawki przeniesione z poprzedniej aplikacji.

WSZYSTKIE WCHODZA JAKO `proponowana`, ZADNA JAKO `zatwierdzona`. Powod nie
jest formalny: przeniesienie liczby z jednego pliku do drugiego nie jest jej
sprawdzeniem, a status `zatwierdzona` ma znaczyc "czlowiek to potwierdzil",
nie "ktos to przepisal". Darek zatwierdza w Ustawieniach, jednym przebiegiem,
widzac przy kazdej pozycji zrodlo i date odczytu.

DOPOKI TEGO NIE ZROBI, SILNIK NIE MA STAWEK I MOWI O TYM WPROST — `BrakStawki`
zamiast kwoty. To jest zamierzone: aplikacja, ktora liczy podatek stawkami,
ktorych nikt nie potwierdzil, wyglada dokladnie tak samo jak aplikacja, ktora
liczy dobrze.

ZRODLO: `../AI CFO/rdzen/stawki.py`, odczyt z biznes.gov.pl i podatki.gov.pl
z 2026-08-25 i 2026-08-26.

CZEGO TU NIE MA I DLACZEGO. Stawek ryczaltu poza jedna (do porownania form) —
Darek jest na skali, a pelna tabela ryczaltu w zasileniu poczatkowym byla
w poprzedniej aplikacji jedna z drog, ktorymi ryczalt wracal jako wartosc
domyslna.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal as D

from wiedza.rejestr import Stawka

_ODCZYT = _dt.date(2026, 8, 25)
_ODCZYT_SKALA = _dt.date(2026, 8, 26)
_OD = _dt.date(2026, 1, 1)

_BIZNES = "https://www.biznes.gov.pl/pl/portal"
_PODATKI = "https://www.podatki.gov.pl"


def _p(klucz: str, wartosc: D, jednostka: str, url: str, opis: str,
       odczyt: _dt.date = _ODCZYT, niezweryfikowane: str | None = None) -> Stawka:
    """Propozycja do zatwierdzenia. Nie ma odpowiednika tworzacego od razu
    `zatwierdzona` — droga maszynowa do zatwierdzenia nie istnieje."""
    return Stawka(
        klucz=klucz, wartosc=wartosc, jednostka=jednostka,
        obowiazuje_od=_OD, obowiazuje_do=None,
        zrodlo_url=url, data_odczytu=odczyt,
        status="proponowana", opis=opis, niezweryfikowane=niezweryfikowane,
    )


#: Skladki spoleczne przedsiebiorcy — DUZY ZUS. Podstawa i stopy osobno,
#: bo kazdy skladnik zaokragla sie OSOBNO: suma niezaokraglonych daje
#: 1 926,77 zamiast 1 926,76. Grosz, ale w przelewie do urzedu.
SPOLECZNE = [
    _p("zus.podstawa_spolecznych", D("5652.00"), "zl", f"{_BIZNES}/00274",
       "Podstawa wymiaru skladek spolecznych, duzy ZUS, 2026."),
    _p("zus.emerytalna", D("0.1952"), "ulamek", f"{_BIZNES}/00274", "Stopa skladki emerytalnej."),
    _p("zus.rentowa", D("0.0800"), "ulamek", f"{_BIZNES}/00274", "Stopa skladki rentowej."),
    _p("zus.chorobowa", D("0.0245"), "ulamek", f"{_BIZNES}/00274", "Stopa chorobowej (dobrowolna, Darek ja placi)."),
    _p("zus.wypadkowa", D("0.0167"), "ulamek", f"{_BIZNES}/00274", "Stopa wypadkowej do 9 ubezpieczonych."),
    _p("zus.fp_fs", D("0.0245"), "ulamek", f"{_BIZNES}/00274", "Fundusz Pracy i Fundusz Solidarnosciowy."),
]

#: Skladka zdrowotna przy SKALI. Podstawa to dochod, nie ryczaltowy mnoznik
#: przecietnego wynagrodzenia — to jest roznica wobec ryczaltu, przez ktora
#: poprzednia aplikacja liczyla zle.
ZDROWOTNA = [
    _p("zdrowotna.stawka_skala", D("0.09"), "ulamek", f"{_BIZNES}/00264",
       "9% dochodu — skala podatkowa."),
    _p("zdrowotna.minimalna_miesieczna", D("432.54"), "zl", f"{_BIZNES}/00264",
       "Dolna granica miesiecznej skladki zdrowotnej przy skali i liniowym."),
]

#: Skala podatkowa 2026.
SKALA = [
    _p("pit.prog_skali", D("120000"), "zl", f"{_BIZNES}/00264",
       "Prog drugiego progu skali.", odczyt=_ODCZYT_SKALA),
    _p("pit.stawka_pierwsza", D("0.12"), "ulamek", f"{_BIZNES}/00264",
       "Stawka do progu.", odczyt=_ODCZYT_SKALA),
    _p("pit.stawka_druga", D("0.32"), "ulamek", f"{_BIZNES}/00264",
       "Stawka powyzej progu.", odczyt=_ODCZYT_SKALA),
    _p("pit.kwota_zmniejszajaca", D("3600"), "zl", f"{_BIZNES}/00264",
       "Kwota zmniejszajaca podatek: 30 000 zl x 12%.", odczyt=_ODCZYT_SKALA),
]

VAT = [
    _p("vat.stawka_podstawowa", D("0.23"), "ulamek", f"{_BIZNES}/00232",
       "Podstawowa stawka VAT."),
    _p("vat.dzien_terminu", D("25"), "zl", f"{_BIZNES}/00232",
       "Dzien miesiaca, do ktorego placi sie VAT za okres poprzedni. "
       "Jednostka 'zl' jest tu naduzyciem — to numer dnia; pozycja do "
       "rozstrzygniecia razem z modelem terminow."),
]

#: Do porownania form (rozdz. 6 PRD). Darek NIE jest na ryczalcie ani na
#: liniowym — te wartosci sluza wylacznie odpowiedzi na pytanie "czy inna
#: forma bylaby lepsza" i nie wolno ich uzyc do policzenia jego podatku.
POROWNANIE_FORM = [
    _p("liniowy.stawka", D("0.19"), "ulamek", f"{_BIZNES}/00264",
       "PORÓWNANIE FORM — podatek liniowy."),
    _p("liniowy.zdrowotna", D("0.049"), "ulamek", f"{_BIZNES}/00264",
       "PORÓWNANIE FORM — zdrowotna przy liniowym."),
    _p("liniowy.limit_odliczenia_zdrowotnej", D("14100"), "zl",
       f"{_PODATKI}/ulgi-i-odliczenia/odliczenie-skladek-na-ubezpieczenie-zdrowotne-pit",
       "PORÓWNANIE FORM — limit odliczenia skladki zdrowotnej.",
       niezweryfikowane="podatki.gov.pl przypisuje te kwote do 2026, "
                        "biznes.gov.pl te sama kwote do 2025. Rozjazd zrodel "
                        "nierozstrzygniety; dotyczy WYLACZNIE liniowego, wiec "
                        "nie wplywa na kwoty Darka."),
    _p("ryczalt.stawka_uslugi_it", D("0.085"), "ulamek", f"{_BIZNES}/00263",
       "PORÓWNANIE FORM — ryczalt dla PKWiU 74.90.19.0. "
       "NIE JEST forma Darka; obecnosc tej wartosci w rejestrze nie upowaznia "
       "zadnego modulu do liczenia ryczaltem."),
]

WSZYSTKIE: list[Stawka] = SPOLECZNE + ZDROWOTNA + SKALA + VAT + POROWNANIE_FORM


def podsumowanie() -> str:
    """Blok do raportu przy zasilaniu. Mowi, ile pozycji czeka na podpis."""
    z_watpliwoscia = [s for s in WSZYSTKIE if s.niezweryfikowane]
    return (
        f"{len(WSZYSTKIE)} stawek w statusie 'proponowana', "
        f"{len(z_watpliwoscia)} z jawna watpliwoscia. "
        f"Zatwierdzonych: 0 — silnik nie policzy nic, dopoki Darek nie podpisze."
    )
