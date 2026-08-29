"""Strazniki reguly D9': "do alokacji" liczy sie WYLACZNIE z planu budzetu.

Pozycja wpisana w plan przestaje byc do dyspozycji w chwili wpisania, nie
w chwili zaplaty — tak samo jak rezerwa na podatki. Wpisy rzeczywiste do tej
liczby nie wchodza wcale; odpowiadaja na inne pytanie i maja wlasna sekcje.
"""

from decimal import Decimal

import pandas as pd

from silnik.rdzen import budzet


def _plan(*krotki) -> pd.DataFrame:
    """Ramka planu z krotek (rok, miesiac, typ, kategoria, kwota)."""
    return pd.DataFrame([
        {"rok": r, "miesiac": m, "typ": t, "kategoria": k,
         "kwota_planowana": Decimal(kw)}
        for r, m, t, k, kw in krotki
    ])


def _wpisy(*krotki) -> pd.DataFrame:
    """Ramka wpisow rzeczywistych z krotek (data, typ, kategoria, kwota)."""
    return pd.DataFrame([
        {"data": d, "typ": t, "kategoria": k, "kwota": Decimal(kw),
         "szczegoly": ""}
        for d, t, k, kw in krotki
    ])


def _listopad() -> pd.DataFrame:
    """Realny plan Darka na listopad 2025, w skrocie do trzech typow."""
    return _plan(
        (2025, 11, "Przychody", "Wynagrodzenie", "6500.00"),
        (2025, 11, "Wydatki", "Kredyty", "3580.00"),
        (2025, 11, "Wydatki", "Zakupy", "5190.00"),
        (2025, 11, "Oszczędności", "Reszta Revolut", "100.00"),
    )


def test_do_alokacji_z_planu_odejmuje_wydatki_i_oszczednosci():
    wynik = budzet.do_alokacji_z_planu(_listopad(), [(2025, 11)])
    assert wynik.kwota == Decimal("-2370.00")
    assert wynik.miesiecy_z_planem == 1
    assert wynik.miesiecy_w_okresie == 1


def test_wpisy_rzeczywiste_NIE_zmieniaja_do_alokacji_z_planu():
    """Glowny straznik D9'. Funkcja nawet nie przyjmuje wpisow."""
    import inspect
    parametry = inspect.signature(budzet.do_alokacji_z_planu).parameters
    assert "wpisy" not in parametry


def test_okres_bez_ani_jednej_pozycji_planu_daje_None_a_NIE_zero():
    """Zero wygladaloby jak budzet spiety co do grosza - najlepszy mozliwy stan."""
    wynik = budzet.do_alokacji_z_planu(_listopad(), [(2026, 9)])
    assert wynik.kwota is None
    assert wynik.miesiecy_z_planem == 0
    assert wynik.miesiecy_w_okresie == 1


def test_plan_wychodzacy_na_zero_daje_ZERO_a_nie_None():
    """Kontrola dwustronna do testu wyzej: zero i brak planu to dwa stany."""
    plan = _plan((2026, 9, "Przychody", "Wynagrodzenie", "100.00"),
                 (2026, 9, "Wydatki", "Zakupy", "100.00"))
    wynik = budzet.do_alokacji_z_planu(plan, [(2026, 9)])
    assert wynik.kwota == Decimal("0.00")
    assert wynik.miesiecy_z_planem == 1


def test_okres_sumuje_miesiace():
    plan = _plan((2025, 10, "Wydatki", "Zakupy", "100.00"),
                 (2025, 11, "Wydatki", "Zakupy", "200.00"),
                 (2025, 12, "Wydatki", "Zakupy", "300.00"))
    wynik = budzet.do_alokacji_z_planu(
        plan, [(2025, 10), (2025, 11), (2025, 12)])
    assert wynik.kwota == Decimal("-600.00")
    assert wynik.miesiecy_z_planem == 3


def test_okres_z_planem_na_czesc_miesiecy_liczy_POKRYCIE():
    """Sama kwota wygladalaby na odpowiedz o caly okres, bedac odpowiedzia
    o jego czesc. Licznik pokrycia zmusza ekran, zeby to powiedzial."""
    wynik = budzet.do_alokacji_z_planu(
        _listopad(), [(2025, 11), (2025, 12), (2026, 1)])
    assert wynik.kwota == Decimal("-2370.00")
    assert wynik.miesiecy_z_planem == 1
    assert wynik.miesiecy_w_okresie == 3


def test_plan_spoza_okresu_nie_wchodzi_do_sumy():
    wynik = budzet.do_alokacji_z_planu(_listopad(), [(2025, 12)])
    assert wynik.kwota is None


def test_sumy_planu_daja_zero_dla_typu_bez_pozycji():
    """Brak klucza znaczylby brak typu, a brak typu wyglada jak zero
    dopiero po tym, jak ktos o tym pomysli."""
    sumy = budzet.sumy_planu(_listopad(), 2025, 11)
    assert set(sumy) == set(budzet.TYPY)
    sumy_pusto = budzet.sumy_planu(_listopad(), 2026, 9)
    assert all(kwota == Decimal("0.00") for kwota in sumy_pusto.values())


def test_stare_do_alokacji_zwraca_niezmieniona_wartosc():
    """Kontrola dwustronna: nowa funkcja nie moze przesunac starej."""
    wpisy = pd.DataFrame([
        {"data": "2025-10-01", "typ": "Przychody", "kategoria": "Wynagrodzenie",
         "kwota": Decimal("8000.00")},
        {"data": "2025-10-05", "typ": "Wydatki", "kategoria": "Zakupy",
         "kwota": Decimal("1000.00")},
    ])
    assert budzet.do_alokacji(wpisy, 2025, 10) == Decimal("7000.00")


# --- Z46: wolne srodki i pozostalo do zaplacenia ---------------------------
# Podatki maja JEDEN nosnik: saldo rezerwy. Kategoria „Podatki i ZUS" jest
# wykluczona z czesci planowej obu liczb, bo inaczej danina wchodzilaby
# dwa razy — raz jako rezerwa, raz jako pozycja planu albo zaplacony wydatek.

def test_wolne_srodki_odejmuja_rezerwe_podatkowa():
    """Decyzja Darka 2026-08-26: podatki pomniejszaja „Wolne srodki".

    Rezerwa to pieniadze, ktore sa na koncie i nie sa Twoje — wolne srodki
    maja o nich wiedziec.
    """
    plan = _plan((2025, 12, "Przychody", "Wynagrodzenie", "6500.00"),
                 (2025, 12, "Wydatki", "Zakupy", "1250.00"),
                 (2025, 12, "Oszczędności", "Reszta Revolut", "100.00"))
    wynik = budzet.wolne_srodki(plan, [(2025, 12)], Decimal("5768.11"))
    assert wynik.kwota == Decimal("-618.11")


def test_wolne_srodki_bez_rezerwy_rowne_alokacji_z_planu():
    """Kontrola dwustronna: przy zerowej rezerwie liczba ma zostac ta sama
    co dzis — inaczej zmiana ruszyla plan, a nie tylko podatki."""
    plan = _plan((2025, 12, "Przychody", "Wynagrodzenie", "6500.00"),
                 (2025, 12, "Wydatki", "Zakupy", "1250.00"))
    assert budzet.wolne_srodki(plan, [(2025, 12)], Decimal("0")).kwota == \
        budzet.do_alokacji_z_planu(plan, [(2025, 12)]).kwota


def test_wolne_srodki_nie_licza_podatkow_dwa_razy():
    """Pozycja planu „Podatki i ZUS" NIE dokłada sie do rezerwy.

    Bez tego wpisanie podatkow do planu — rzecz zupelnie naturalna —
    odejmowaloby te sama danine dwa razy.
    """
    plan = _plan((2025, 12, "Przychody", "Wynagrodzenie", "6500.00"),
                 (2025, 12, "Wydatki", budzet.KATEGORIA_PODATKI, "5768.11"))
    wynik = budzet.wolne_srodki(plan, [(2025, 12)], Decimal("5768.11"))
    assert wynik.kwota == Decimal("731.89")


def test_wolne_srodki_odejmuja_rezerwe_RAZ_w_okresie_wielomiesiecznym():
    """Rezerwa to saldo jednego dlugu, nie kwota miesieczna — przy okresie
    trzymiesiecznym odejmuje sie raz, nie trzy razy."""
    plan = _plan((2025, 10, "Przychody", "Wynagrodzenie", "1000.00"),
                 (2025, 11, "Przychody", "Wynagrodzenie", "1000.00"),
                 (2025, 12, "Przychody", "Wynagrodzenie", "1000.00"))
    wynik = budzet.wolne_srodki(
        plan, [(2025, 10), (2025, 11), (2025, 12)], Decimal("100.00"))
    assert wynik.kwota == Decimal("2900.00")


def test_brak_planu_zostaje_brakiem_planu_mimo_rezerwy():
    """Sama rezerwa nie tworzy planu — „nie wiadomo" zostaje „nie wiadomo"
    (decyzja D11)."""
    assert budzet.wolne_srodki(_plan(), [(2025, 12)],
                               Decimal("5768.11")).kwota is None


def test_pozostalo_do_zaplacenia_maleje_z_kazda_transakcja():
    """Sedno zgloszenia Darka: kafelek pokazuje, ile jeszcze trzeba zaplacic,
    i maleje w miare wprowadzania transakcji — jak kolumna Remaining
    w arkuszu."""
    plan = _plan((2025, 12, "Wydatki", "Zakupy", "1000.00"))
    wpisy = _wpisy(("2025-12-05", "Wydatki", "Zakupy", "300.00"))
    stan = budzet.pozostalo_do_zaplacenia(wpisy, plan, [(2025, 12)],
                                          Decimal("0"))
    assert stan.zaplanowane == Decimal("1000.00")
    assert stan.zaplacone == Decimal("300.00")
    assert stan.pozostalo == Decimal("700.00")


def test_pozostalo_do_zaplacenia_zawiera_rezerwe_podatkowa():
    """Decyzja Darka: podatki POWIEKSZAJA kafelek wydatkow."""
    plan = _plan((2025, 12, "Wydatki", "Zakupy", "1000.00"))
    stan = budzet.pozostalo_do_zaplacenia(_wpisy(), plan, [(2025, 12)],
                                          Decimal("5768.11"))
    assert stan.podatki == Decimal("5768.11")
    assert stan.pozostalo == Decimal("6768.11")


def test_zaplacona_danina_nie_liczy_sie_drugi_raz_jako_wydatek():
    """Zaplata daniny tworzy wpis w kategorii „Podatki i ZUS" (przycisk
    „Zaplacone" w zakladce JDG) i JEDNOCZESNIE zbija saldo rezerwy. Gdyby ten
    wpis wchodzil takze do czesci planowej, kafelek spadlby o kwote daniny
    dwa razy."""
    plan = _plan((2025, 12, "Wydatki", "Zakupy", "1000.00"))
    wpisy = _wpisy(("2025-12-20", "Wydatki", budzet.KATEGORIA_PODATKI, "767.00"))
    stan = budzet.pozostalo_do_zaplacenia(wpisy, plan, [(2025, 12)],
                                          Decimal("5001.11"))
    assert stan.zaplacone == Decimal("0.00")
    assert stan.pozostalo == Decimal("6001.11")


def test_przekroczony_plan_jest_nazwany_wprost():
    """Ujemne „pozostalo" bez slowa wyjasnienia wyglada jak wada obliczen."""
    plan = _plan((2025, 10, "Wydatki", "Zakupy", "1000.00"))
    wpisy = _wpisy(("2025-10-05", "Wydatki", "Zakupy", "1500.00"))
    stan = budzet.pozostalo_do_zaplacenia(wpisy, plan, [(2025, 10)],
                                          Decimal("0"))
    assert stan.przekroczony_plan is True
    assert stan.pozostalo == Decimal("-500.00")


def test_plan_niewykonany_nie_jest_przekroczeniem():
    """Kontrola dwustronna do testu wyzej."""
    plan = _plan((2025, 10, "Wydatki", "Zakupy", "1000.00"))
    stan = budzet.pozostalo_do_zaplacenia(_wpisy(), plan, [(2025, 10)],
                                          Decimal("0"))
    assert stan.przekroczony_plan is False
