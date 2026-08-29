"""Strażnicy zachowania transakcyjnego — po podmianie sterownika (W4).

DLACZEGO TE TESTY POWSTAŁY PRZED W4 I CO SIĘ Z NIMI STAŁO. Napisano je jeszcze
na SQLite, bo tam stan poprawny był jeszcze widoczny: połączenie było brane na
żądanie HTTP i zamykane w `finally`, więc porzucona transakcja znikała razem
z połączeniem i wady nie było czuć. W PostgreSQL to samo połączenie bywa
oddawane do puli, a transakcja zostawiona otwarta blokuje wiersze i przenosi
się na następne żądanie.

DWIE KLASY, OBIE DOMKNIĘTE:

1. **Zapis, po którym leci wyjątek bez `rollback()`** — naprawione w W2.
   Pomiar (AST, 2026-08-29) znalazł **sześć** takich miejsc, nie trzy, jak
   mówił plan sesji. Wszystkie sześć dostały `rollback()` przed `raise`.

2. **Dwa zapisy z `commit` w środku** (`zapisz_koszt`,
   `oznacz_fakture_zaplacona`) — świadomie odłożone do W4 z jawnym progiem:
   „te dwa strażniki mają wtedy zaczerwienić się CELOWO". **Próg zadziałał
   2026-08-29.** Obie funkcje robią teraz oba zapisy w JEDNYM bloku
   `with polaczenie.transaction()`, więc awaria drugiego zapisu nie zostawia
   osieroconego wpisu budżetu. Strażniki opisujące stan odłożony zostały
   ODWRÓCONE — nie zdjęte: pilnują teraz, że atomowość JEST, a nie że jej nie
   ma. Poprzednie brzmienie stoi w `testy/MUTACJE.md`.

   ROZWIĄZANIE NIE JEST TYM, KTÓRE ZAPOWIADAŁ NAGŁÓWEK. Zapowiadał „jeden blok
   `with polaczenie:` obejmuje oba zapisy" — a tak się nie da: wewnętrzny
   `zapisz_wpis` woła `commit()`, a `commit()` w środku bloku transakcji
   psycopg jest błędem. Zamiast tego reguły wpisu budżetu zostały wydzielone
   do `magazyn._przygotuj_wpis` (jeden nośnik reguł, zero zapisu), a dwie
   polityki zatwierdzania mieszkają u dwóch wołających.
"""

from __future__ import annotations

import ast
import pathlib
import re
from datetime import date
from decimal import Decimal

import pytest

import psycopg

from silnik.rdzen import magazyn

PISZACE_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", re.I)

#: Funkcje, które robią DWA zapisy o jednym znaczeniu — i dlatego muszą je
#: robić w JEDNEJ transakcji. Do W4 były to „dwa zapisy, dwa zatwierdzenia".
ATOMOWE = ("zapisz_koszt", "oznacz_fakture_zaplacona")


@pytest.fixture
def polaczenie():
    p = magazyn.zmigruj_i_polacz()
    yield p
    p.close()


def _czy_w_transakcji(polaczenie) -> bool:
    """Czy na tym połączeniu wisi otwarta transakcja.

    NASTĘPCA `Connection.in_transaction` ze sterownika SQLite, którego psycopg
    nie ma. Odpowiedź daje `info.transaction_status`: `IDLE` znaczy „nic nie
    wisi", każdy inny stan (w tym `INERROR`) znaczy, że wisi — a `INERROR` jest
    groźniejszy niż `INTRANS`, bo na takim połączeniu każde następne polecenie
    odbija się błędem, dopóki ktoś nie zawoła `rollback()`.
    """
    return polaczenie.info.transaction_status != psycopg.pq.TransactionStatus.IDLE


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
        # `with polaczenie.transaction():` liczy się jak `rollback()` — i to
        # NIE jest ustępstwo. Ten blok wycofuje transakcję przy KAŻDYM wyjściu
        # przez wyjątek, także przez taki, którego autor nie przewidział;
        # ręczny `rollback()` wycofuje tylko to, co ktoś objął `except`.
        # Bez tego rozpoznania strażnik czerwieniłby się na naprawie MOCNIEJSZEJ
        # niż ta, której pilnuje (zmierzone 2026-08-29 po W4: dwa fałszywe
        # trafienia — `zapisz_koszt` i `oznacz_fakture_zaplacona`).
        bloki = [w for w in ast.walk(f) if isinstance(w, ast.With)
                 for poz in w.items
                 if isinstance(poz.context_expr, ast.Call)
                 and getattr(poz.context_expr.func, "attr", "") == "transaction"]
        if raisy and not rollbacki and not bloki:
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
    assert not _czy_w_transakcji(polaczenie), \
        "po odmowie została otwarta transakcja"


def test_odmowa_kasowania_kategorii_NIE_ZOSTAWIA_otwartej_transakcji(polaczenie):
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.usun_kategorie_trwale(
            polaczenie, typ="Wydatki", nazwa="Nie ma takiej")
    assert not _czy_w_transakcji(polaczenie), \
        "po odmowie została otwarta transakcja"


# --- klasa 2: dwa zapisy o jednym znaczeniu — JEDNA transakcja ------------

def _policz_zatwierdzenia(polaczenie, czynnosc):
    """Ile razy transakcja została zatwierdzona w trakcie `czynnosc`.

    NASTĘPCA `set_trace_callback` ze sterownika SQLite, którego psycopg nie ma.
    Liczymy wywołania `commit()` NA POŁĄCZENIU — łącznie z tym, które psycopg
    wykonuje sam przy wyjściu z bloku `with polaczenie.transaction()`.
    """
    licznik = {"n": 0}
    prawdziwy = type(polaczenie).commit

    def liczacy(self, *a, **k):
        licznik["n"] += 1
        return prawdziwy(self, *a, **k)

    prawdziwy_wyjscie = psycopg.Transaction.__exit__

    def liczace_wyjscie(self, typ, wartosc, slad):
        wynik = prawdziwy_wyjscie(self, typ, wartosc, slad)
        if typ is None:
            licznik["n"] += 1
        return wynik

    type(polaczenie).commit = liczacy
    psycopg.Transaction.__exit__ = liczace_wyjscie
    try:
        czynnosc()
    finally:
        type(polaczenie).commit = prawdziwy
        psycopg.Transaction.__exit__ = prawdziwy_wyjscie
    return licznik["n"]


def test_zapisz_koszt_ZATWIERDZA_RAZ_a_nie_dwa_razy(polaczenie):
    """ODWRÓCONY strażnik stanu odłożonego. Do W4 asercja brzmiała `== 2`.

    Dwa zatwierdzenia znaczyły: wydatek w budżecie jest już nieodwracalnie
    w bazie, gdy wiersz kosztu dopiero się zapisuje. Teraz oba zapisy siedzą
    w jednym bloku transakcji, więc zatwierdzenie jest jedno — a jego liczba
    jest tu KONTROLĄ LICZNOŚCI, nie ozdobą: zero znaczyłoby, że sonda niczego
    nie zobaczyła.
    """
    ile = _policz_zatwierdzenia(polaczenie, lambda: magazyn.zapisz_koszt(
        polaczenie, data=date(2026, 9, 5), opis="laptop",
        kwota_netto=Decimal("1000.00"), kwota_vat=Decimal("230.00")))
    assert ile == 1, \
        (f"zatwierdzeń było {ile}, ma być jedno — oba zapisy należą do jednej "
         "transakcji")


def test_zapisz_koszt_NIE_ZOSTAWIA_osieroconego_wpisu_gdy_drugi_zapis_padnie(
        polaczenie, monkeypatch):
    """SEDNO NAPRAWY, zmierzone skutkiem, nie kształtem kodu.

    Do W4 pierwszy zapis (wydatek w budżecie) był już zatwierdzony, gdy drugi
    (wiersz kosztu) padał — zostawał wydatek `Firmowe` bez kosztu, czyli
    dokładnie ten stan, przed którym ostrzega nagłówek `usun_koszt`. Teraz
    pada wszystko albo nic.
    """
    przed = len(magazyn.wczytaj_wpisy(polaczenie))
    prawdziwy = psycopg.Cursor.execute

    def padnij(self, query, params=None, **k):
        if isinstance(query, str) and "koszty_jdg" in query:
            raise psycopg.OperationalError("awaria drugiego zapisu (test)")
        return prawdziwy(self, query, params, **k)

    monkeypatch.setattr(psycopg.Cursor, "execute", padnij)
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_koszt(polaczenie, data=date(2026, 9, 5), opis="laptop",
                             kwota_netto=Decimal("1000.00"),
                             kwota_vat=Decimal("230.00"))
    monkeypatch.undo()

    po = len(magazyn.wczytaj_wpisy(polaczenie))
    assert po == przed, \
        (f"osierocony wpis budżetu został w bazie ({przed} -> {po}) — "
         "transakcja nie objęła obu zapisów")
    assert magazyn.wczytaj_koszty(polaczenie).empty


def test_oznacz_fakture_ZATWIERDZA_RAZ_a_nie_dwa_razy(polaczenie):
    """Ta sama klasa co wyżej. Do W4 asercja brzmiała `== 2`.

    Faktura zapisana BEZ stawki ryczałtu, bo Darek jest na SKALI — od W4
    kolumna dopuszcza brak wartości i to jest właściwa odpowiedź, a nie zero.
    """
    fid = magazyn.zapisz_fakture(
        polaczenie, data=date(2026, 9, 1), numer_faktury="1/2026",
        kwota_netto=Decimal("10000.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2300.00"), pkwiu="62.01.11",
        zaplacony_zus=Decimal("0"), zysk_netto=Decimal("0"),
        stawki_wersja="test")

    ile = _policz_zatwierdzenia(polaczenie, lambda:
        magazyn.oznacz_fakture_zaplacona(polaczenie, faktura_id=fid,
                                         data_wplywu=date(2026, 9, 20)))
    assert ile == 1, \
        f"zatwierdzeń było {ile}, ma być jedno"


def test_oznacz_fakture_NIE_ZOSTAWIA_przychodu_bez_daty_wplywu(
        polaczenie, monkeypatch):
    """Druga strona tej samej naprawy — i skutek, który widziałby Darek.

    Gdyby zapis przychodu przeszedł, a `UPDATE` daty wpływu padł, faktura
    zostałaby NIEZAPŁACONA przy istniejącym przychodzie w budżecie — czyli
    „do alokacji" podniosłoby się o całą fakturę, a przy następnej próbie
    oznaczenia przychód policzyłby się drugi raz.
    """
    fid = magazyn.zapisz_fakture(
        polaczenie, data=date(2026, 9, 1), numer_faktury="2/2026",
        kwota_netto=Decimal("10000.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2300.00"), pkwiu="62.01.11",
        zaplacony_zus=Decimal("0"), zysk_netto=Decimal("0"),
        stawki_wersja="test")
    przed = len(magazyn.wczytaj_wpisy(polaczenie))
    prawdziwy = psycopg.Cursor.execute

    def padnij(self, query, params=None, **k):
        if isinstance(query, str) and "UPDATE przychody_jdg" in query:
            raise psycopg.OperationalError("awaria drugiego zapisu (test)")
        return prawdziwy(self, query, params, **k)

    monkeypatch.setattr(psycopg.Cursor, "execute", padnij)
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.oznacz_fakture_zaplacona(polaczenie, faktura_id=fid,
                                         data_wplywu=date(2026, 9, 20))
    monkeypatch.undo()

    assert len(magazyn.wczytaj_wpisy(polaczenie)) == przed, \
        "przychód w budżecie został, choć data wpływu się nie zapisała"


def test_lista_ATOMOWYCH_jest_KOMPLETNA():
    """Zakres naprawy ma być jawny: dokładnie dwie nazwane funkcje.

    Gdyby doszła trzecia, ten test ma o niej powiedzieć — reguła bez strażnika
    jest długiem ukrytym, nie decyzją (§3.2).
    """
    zrodlo = pathlib.Path("silnik/rdzen/magazyn.py").read_text(encoding="utf-8")
    for nazwa in ATOMOWE:
        assert f"def {nazwa}(" in zrodlo, f"zniknęła funkcja {nazwa}"
        ciало = zrodlo[zrodlo.index(f"def {nazwa}("):]
        ciало = ciало[:ciало.index("\ndef ", 1)]
        assert "with polaczenie.transaction()" in ciало, \
            (f"{nazwa} robi dwa zapisy poza wspólną transakcją — awaria "
             "drugiego zostawi osierocony wiersz")
    assert len(ATOMOWE) == 2
