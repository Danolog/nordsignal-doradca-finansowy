"""Strazniki rozwijania regul planu do jednego miesiaca (Z42).

Pozycja oznaczona jako powtarzalna obowiazuje OD swojego miesiaca do odwolania,
wiec „plan na wrzesien" przestal byc filtrem po wierszach wrzesniowych i stal
sie pytaniem „ktora wersja tej pozycji obowiazuje we wrzesniu".

Kontrola dwustronna jest tu regula, nie ozdoba: kazdy straznik pokazujacy, ze
pozycja trwala PRZECHODZI dalej, ma pare pokazujaca, ze jednorazowa NIE
przechodzi. Sam pierwszy przeszedlby tez wtedy, gdyby rozwijacz przepuszczal
wszystko.
"""

from decimal import Decimal

import pandas as pd

from silnik.rdzen import budzet


def _plan(*wiersze) -> pd.DataFrame:
    """Ramka planu w ksztalcie, jaki daje `magazyn.wczytaj_plan`."""
    return pd.DataFrame([
        {"id": i + 1, "rok": rok, "miesiac": miesiac, "typ": typ,
         "kategoria": kategoria, "kwota_planowana": Decimal(kwota),
         "powtarzalna": powtarzalna, "do_roku": do_roku,
         "do_miesiaca": do_miesiaca}
        for i, (rok, miesiac, typ, kategoria, kwota, powtarzalna, do_roku,
                do_miesiaca) in enumerate(wiersze)
    ])


TRWALA_OD_WRZESNIA = (2026, 9, "Wydatki", "Zakupy", "100.00", 1, None, None)
JEDNORAZOWA_WRZESNIOWA = (2026, 9, "Wydatki", "Zakupy", "100.00", 0, None, None)


def test_pozycja_trwala_obowiazuje_w_nastepnym_miesiacu():
    wynik = budzet.plan_na_miesiac(_plan(TRWALA_OD_WRZESNIA), 2026, 10)
    assert len(wynik) == 1
    assert wynik.iloc[0]["kwota_planowana"] == Decimal("100.00")


def test_pozycja_jednorazowa_nie_przechodzi_do_nastepnego_miesiaca():
    """Para kontrolna testu wyzej — bez niej „przechodzi" byloby prawda
    takze wtedy, gdyby rozwijacz nie patrzyl na `powtarzalna` wcale."""
    assert budzet.plan_na_miesiac(_plan(JEDNORAZOWA_WRZESNIOWA),
                                  2026, 10).empty


def test_pozycja_jednorazowa_jest_widoczna_w_swoim_miesiacu():
    """Druga strona kontroli: „nie przechodzi" nie moze znaczyc „znika calkiem"."""
    assert len(budzet.plan_na_miesiac(_plan(JEDNORAZOWA_WRZESNIOWA),
                                      2026, 9)) == 1


def test_pozycja_trwala_nie_jest_widoczna_przed_swoim_miesiacem():
    """Regula obowiazuje OD swojego miesiaca — wstecz nie dziala.

    Bez tego straznika „do odwolania" cofaloby sie takze w przeszlosc
    i zmienialo zamkniete miesiace, ktorych Darek juz nie oglada.
    """
    assert budzet.plan_na_miesiac(_plan(TRWALA_OD_WRZESNIA), 2026, 8).empty


def test_nowsza_wersja_kwoty_wygrywa_od_swojego_miesiaca():
    """Decyzja Darka nr 3: zmiana dziala OD wskazanego miesiaca w przod."""
    plan = _plan(
        (2026, 1, "Wydatki", "Zakupy", "200.00", 1, None, None),
        (2026, 4, "Wydatki", "Zakupy", "260.00", 1, None, None),
    )
    marzec = budzet.plan_na_miesiac(plan, 2026, 3)
    kwiecien = budzet.plan_na_miesiac(plan, 2026, 4)
    assert marzec.iloc[0]["kwota_planowana"] == Decimal("200.00")
    assert kwiecien.iloc[0]["kwota_planowana"] == Decimal("260.00")


def test_dwie_wersje_tej_samej_pozycji_daja_jeden_wiersz():
    """Kontrola licznosci: rozwiniecie ma WYBRAC wersje, nie zsumowac obu.

    Bez tej asercji test wyzej przeszedlby takze wtedy, gdyby ramka niosla
    dwa wiersze, a `iloc[0]` trafialo w ten wlasciwy przypadkiem.
    """
    plan = _plan(
        (2026, 1, "Wydatki", "Zakupy", "200.00", 1, None, None),
        (2026, 4, "Wydatki", "Zakupy", "260.00", 1, None, None),
    )
    assert len(budzet.plan_na_miesiac(plan, 2026, 6)) == 1


def test_regula_zamknieta_znika_od_nastepnego_miesiaca():
    plan = _plan((2026, 9, "Wydatki", "Zakupy", "100.00", 1, 2026, 10))
    assert len(budzet.plan_na_miesiac(plan, 2026, 10)) == 1
    assert budzet.plan_na_miesiac(plan, 2026, 11).empty


def test_rozwiniecie_przechodzi_przez_nowy_rok():
    """Os absolutna, nie sam numer miesiaca: 2026-11 obowiazuje w 2027-01.

    Porownanie po samym `miesiac` daloby tu 11 > 1 i uznaloby regule za
    jeszcze nierozpoczeta.
    """
    plan = _plan((2026, 11, "Wydatki", "Zakupy", "100.00", 1, None, None))
    assert len(budzet.plan_na_miesiac(plan, 2027, 1)) == 1


def test_regula_zamknieta_w_grudniu_znika_w_styczniu():
    """Ta sama os absolutna po stronie konca obowiazywania."""
    plan = _plan((2026, 9, "Wydatki", "Zakupy", "100.00", 1, 2026, 12))
    assert len(budzet.plan_na_miesiac(plan, 2026, 12)) == 1
    assert budzet.plan_na_miesiac(plan, 2027, 1).empty


def test_pusty_plan_daje_pusta_ramke_a_nie_wyjatek():
    """Pusta ramka nie ma kolumn — odwolanie do `plan[\"rok\"]` rzucaloby KeyError."""
    assert budzet.plan_na_miesiac(pd.DataFrame(), 2026, 9).empty


def test_ramka_bez_kolumny_powtarzalna_znaczy_jednorazowa():
    """Jeden nosnik znaczenia domyslnego: `DEFAULT 0` w bazie i `get(..., 0)` tutaj.

    Ramki bez tej kolumny buduja starsze testy i kod, ktory jeszcze nie wie
    o Z42 — musza zachowywac sie dokladnie jak dzis.
    """
    plan = pd.DataFrame([
        {"rok": 2026, "miesiac": 9, "typ": "Wydatki", "kategoria": "Zakupy",
         "kwota_planowana": Decimal("100.00")}])
    assert len(budzet.plan_na_miesiac(plan, 2026, 9)) == 1
    assert budzet.plan_na_miesiac(plan, 2026, 10).empty


def test_rozne_kategorie_nie_konkuruja_ze_soba():
    """Wybor „najpozniejszy start" dotyczy pary (typ, kategoria), nie planu."""
    plan = _plan(
        (2026, 1, "Wydatki", "Zakupy", "200.00", 1, None, None),
        (2026, 4, "Wydatki", "Transport", "50.00", 1, None, None),
        (2026, 4, "Przychody", "Zakupy", "9000.00", 1, None, None),
    )
    assert len(budzet.plan_na_miesiac(plan, 2026, 6)) == 3
