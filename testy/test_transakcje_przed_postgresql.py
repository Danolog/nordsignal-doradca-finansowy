# -*- coding: utf-8 -*-
"""Strażnicy zachowania transakcyjnego — postawione PRZED podmianą sterownika.

DLACZEGO TERAZ, A NIE PRZY W4. W SQLite z domyślnym trybem sterownika te
zachowania są niewidoczne: połączenie jest brane na żądanie HTTP i zamykane
w `finally`, więc porzucona transakcja i tak znika razem z połączeniem.
W PostgreSQL to samo połączenie bywa oddawane do puli, a transakcja zostawiona
otwarta blokuje wiersze i przenosi się na następne żądanie. Test napisany po
podmianie sterownika nie miałby z czym porównać — stan poprawny byłby już
niewidoczny.

DWIE KLASY, ROZSTRZYGNIĘTE INACZEJ:

1. **Zapis, po którym leci wyjątek bez `rollback()`** — NAPRAWIONE w W2.
   Pomiar (AST, 2026-08-29) znalazł **sześć** takich miejsc, nie trzy, jak
   mówił plan sesji. Wszystkie sześć dostały `rollback()` przed `raise`.

2. **Dwa zapisy z `commit` w środku** (`zapisz_koszt`,
   `oznacz_fakture_zaplacona`) — ŚWIADOMIE ODŁOŻONE do W4, bo poprawny
   kształt naprawy zależy od sterownika: w psycopg jeden blok `with
   polaczenie:` obejmuje oba zapisy, a przewlekanie znacznika „nie zatwierdzaj"
   przez `zapisz_wpis` i `_zapisz` byłoby rusztowaniem, które W4 natychmiast
   wyrzuca. Odłożenie NIE jest ciche: poniżej stoją strażniki, które opisują
   dzisiejszy skutek, plus jawny próg.

   **PRÓG KONSOLIDACJI: podmiana sterownika na PostgreSQL (W4).** Te dwa
   strażniki mają wtedy zaczerwienić się CELOWO — ich czerwień jest sygnałem
   „napraw atomowość teraz", a nie regresją.
"""

from __future__ import annotations

import ast
import pathlib
import re
from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import magazyn

PISZACE_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", re.I)

#: Ile miejsc „dwa zapisy, dwa zatwierdzenia" zostaje świadomie do W4.
ODLOZONE_DO_W4 = ("zapisz_koszt", "oznacz_fakture_zaplacona")


@pytest.fixture
def polaczenie(tmp_path):
    p = magazyn.zmigruj_i_polacz(tmp_path / "transakcje.db")
    yield p
    p.close()


# --- klasa 1: zapis, po którym leci wyjątek -------------------------------

def test_ZADNA_funkcja_nie_zglasza_bledu_po_zapisie_bez_rollback():
    """Strażnik ŹRÓDŁOWY całej klasy, nie trzech wymienionych miejsc.

    Plan sesji wymieniał trzy funkcje. Pomiar znalazł sześć — dokładnie ta
    sama klasa pomyłki co przy W1 („dziewięć rozjazdów" wobec 24 zmierzonych).
    Dlatego strażnik liczy WSZYSTKIE funkcje modułu, a nie sprawdza listy nazw.
    """
    drzewo = ast.parse(
        pathlib.Path("silnik/rdzen/magazyn.py").read_text(encoding="utf-8"))
    funkcje = [w for w in ast.walk(drzewo) if isinstance(w, ast.FunctionDef)]

    piszace, winne = 0, []
    for f in funkcje:
        zapisy = [w.lineno for w in ast.walk(f)
                  if isinstance(w, ast.Call)
                  and getattr(w.func, "attr", "") in ("execute", "executescript")
                  for a in w.args
                  if isinstance(a, ast.Constant) and isinstance(a.value, str)
                  and PISZACE_SQL.search(a.value)]
        if not zapisy:
            continue
        piszace += 1
        raisy = [w.lineno for w in ast.walk(f)
                 if isinstance(w, ast.Raise) and w.lineno > min(zapisy)]
        rollbacki = [w for w in ast.walk(f) if isinstance(w, ast.Call)
                     and getattr(w.func, "attr", "") == "rollback"]
        if raisy and not rollbacki:
            winne.append(f"{f.name} (linia {f.lineno})")

    # KONTROLA LICZNOŚCI: bez niej ten test przechodzi także wtedy, gdy parser
    # nie zobaczył ani jednej funkcji — czyli porównuje pustkę z pustką.
    assert len(funkcje) >= 80, f"parser zobaczył tylko {len(funkcje)} funkcji"
    assert piszace >= 20, f"parser zobaczył tylko {piszace} funkcji piszących"
    assert winne == [], \
        ("zapis, po którym leci wyjątek bez `rollback()` — w PostgreSQL "
         f"zostawia otwartą transakcję na połączeniu z puli: {winne}")


def test_odmowa_dezaktywacji_NIE_ZOSTAWIA_otwartej_transakcji(polaczenie):
    """Zachowanie, nie kształt źródła: `UPDATE` trafił w zero wierszy."""
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.ustaw_aktywnosc_kategorii(
            polaczenie, typ="Wydatki", nazwa="Nie ma takiej", aktywna=False)
    assert not polaczenie.in_transaction, \
        "po odmowie została otwarta transakcja"


def test_odmowa_kasowania_kategorii_NIE_ZOSTAWIA_otwartej_transakcji(polaczenie):
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.usun_kategorie_trwale(
            polaczenie, typ="Wydatki", nazwa="Nie ma takiej")
    assert not polaczenie.in_transaction, \
        "po odmowie została otwarta transakcja"


# --- klasa 2: dwa zapisy, dwa zatwierdzenia — ODŁOŻONE do W4 --------------

def _policz_zatwierdzenia(polaczenie, czynnosc):
    zapis: list[str] = []
    polaczenie.set_trace_callback(zapis.append)
    try:
        czynnosc()
    finally:
        polaczenie.set_trace_callback(None)
    assert zapis, "podsłuch nie zobaczył ani jednego polecenia"
    return len([x for x in zapis if x.strip().upper().startswith("COMMIT")])


def test_zapisz_koszt_ROBI_DWA_ZATWIERDZENIA_stan_odlozony(polaczenie):
    """Stan dzisiejszy, zapisany liczbą. **PRÓG: podmiana sterownika (W4).**"""
    ile = _policz_zatwierdzenia(polaczenie, lambda: magazyn.zapisz_koszt(
        polaczenie, data=date(2026, 9, 5), opis="laptop",
        kwota_netto=Decimal("1000.00"), kwota_vat=Decimal("230.00")))
    assert ile == 2, \
        (f"zatwierdzeń było {ile}, nie 2 — jeśli to skutek naprawy atomowości "
         "w W4, zaktualizuj ten strażnik i nagłówek pliku")


def test_zapisz_koszt_ZOSTAWIA_OSIEROCONY_wpis_gdy_drugi_zapis_padnie(
        polaczenie, monkeypatch):
    """SKUTEK odłożenia, nazwany wprost — nie „do przemyślenia później".

    Pierwszy zapis (wydatek w budżecie) jest już zatwierdzony, gdy drugi
    (wiersz kosztu) pada. Zostaje wydatek `Firmowe` bez kosztu — czyli
    dokładnie ten stan, przed którym ostrzega nagłówek `usun_koszt`.
    """
    przed = len(magazyn.wczytaj_wpisy(polaczenie))
    prawdziwy = magazyn._zapisz

    def padnij(pol, sql, wartosci):
        if "koszty_jdg" in sql:
            raise magazyn.BladMagazynu("awaria drugiego zapisu (test)")
        return prawdziwy(pol, sql, wartosci)

    monkeypatch.setattr(magazyn, "_zapisz", padnij)
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_koszt(polaczenie, data=date(2026, 9, 5), opis="laptop",
                             kwota_netto=Decimal("1000.00"),
                             kwota_vat=Decimal("230.00"))

    po = len(magazyn.wczytaj_wpisy(polaczenie))
    assert po == przed + 1, \
        ("stan odłożony: osierocony wpis budżetu miał zostać. Jeśli zniknął, "
         "atomowość została naprawiona — zdejmij ten strażnik przy W4")
    assert magazyn.wczytaj_koszty(polaczenie).empty


def test_oznacz_fakture_ROBI_DWA_ZATWIERDZENIA_stan_odlozony(polaczenie):
    """Ta sama klasa co wyżej. **PRÓG: podmiana sterownika (W4).**

    Faktura zapisana ze `stawka_ryczaltu = 0`, bo Darek jest na SKALI —
    kolumna jest wymagana przez schemat, nie przez rachunek.
    """
    fid = magazyn.zapisz_fakture(
        polaczenie, data=date(2026, 9, 1), numer_faktury="1/2026",
        kwota_netto=Decimal("10000.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2300.00"), pkwiu="62.01.11",
        stawka_ryczaltu=Decimal("0"), zaplacony_zus=Decimal("0"),
        zysk_netto=Decimal("0"), stawki_wersja="test")

    ile = _policz_zatwierdzenia(polaczenie, lambda:
        magazyn.oznacz_fakture_zaplacona(polaczenie, faktura_id=fid,
                                         data_wplywu=date(2026, 9, 20)))
    assert ile == 2, \
        (f"zatwierdzeń było {ile}, nie 2 — jeśli to skutek naprawy atomowości "
         "w W4, zaktualizuj ten strażnik i nagłówek pliku")


def test_lista_odlozonych_do_W4_jest_KOMPLETNA():
    """Odłożenie ma jawny zakres: dokładnie dwie nazwane funkcje.

    Gdyby doszła trzecia, ten test ma o niej powiedzieć — dług odłożony bez
    progu i bez strażnika jest długiem ukrytym, nie decyzją (§3.2).
    """
    zrodlo = pathlib.Path("silnik/rdzen/magazyn.py").read_text(encoding="utf-8")
    for nazwa in ODLOZONE_DO_W4:
        assert f"def {nazwa}(" in zrodlo, f"zniknęła funkcja {nazwa}"
    assert len(ODLOZONE_DO_W4) == 2
