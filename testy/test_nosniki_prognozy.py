"""Dwa nosniki upublicznione dla prognozy plynnosci (Z61).

Prognoza ma WOLAC istniejace reguly, nie kopiowac ich. Dwie z nich byly
niedostepne:

1. `budzet._bez_podatkow` — prywatna. Regula „danina ma w tej aplikacji jeden
   nosnik: saldo rezerwy" jest tym filtrem; skopiowana do prognozy dalaby
   podwojne liczenie podatku, czyli dokladnie to ryzyko nr 2 z planu.
2. Regula „dzien wiekszy niz dlugosc miesiaca znaczy OSTATNI dzien" byla
   **udokumentowana w `magazyn._wymagaj_dnia` i nigdzie niezaimplementowana**.
   Prognoza jest jej pierwszym konsumentem: pozycja planu platna 31. musi
   trafic w luty, bo inaczej wypada z osi dziennej bez sladu.
"""

from datetime import date

import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn, terminy


def _plan(*wiersze) -> pd.DataFrame:
    return pd.DataFrame(
        [{"rok": r, "miesiac": m, "typ": t, "kategoria": k,
          "kwota_planowana": kw, "powtarzalna": 0, "opis": "", "dzien": None,
          "co_ile_miesiecy": 1}
         for r, m, t, k, kw in wiersze])


# --- nosnik 1: bez_podatkow jest publiczny -------------------------------

def test_bez_podatkow_jest_PUBLICZNY_i_odsiewa_podatki():
    """Kryterium Z61. Prognoza nie ma prawa siegac po nazwe z podkresleniem —
    a skopiowanie filtru bylo by drugim nosnikiem reguly o podwojnym podatku."""
    plan = _plan((2026, 9, budzet.TYP_WYDATKI, "Zakupy", "100.00"),
                 (2026, 9, budzet.TYP_WYDATKI, budzet.KATEGORIA_PODATKI, "900.00"),
                 (2026, 9, budzet.TYP_PRZYCHODY, "Wynagrodzenie", "8000.00"))
    assert len(plan) == 3, "kontrola licznosci: pomiar musi cos widziec"

    zostaje = budzet.bez_podatkow(plan)

    assert len(zostaje) == 2
    assert budzet.KATEGORIA_PODATKI not in set(zostaje["kategoria"])
    assert set(zostaje["kategoria"]) == {"Zakupy", "Wynagrodzenie"}


def test_bez_podatkow_ZOSTAWIA_wszystko_gdy_nie_ma_daniny():
    """Kontrola dwustronna: filtr, ktory odsiewa zawsze, nie jest filtrem."""
    plan = _plan((2026, 9, budzet.TYP_WYDATKI, "Zakupy", "100.00"),
                 (2026, 9, budzet.TYP_WYDATKI, "Transport", "50.00"))
    assert len(budzet.bez_podatkow(plan)) == 2


def test_bez_podatkow_przepuszcza_PUSTA_ramke():
    """Brak planu to normalny stan, nie awaria — prognoza dostanie go
    w kazdym miesiacu bez pokrycia."""
    assert budzet.bez_podatkow(pd.DataFrame()).empty


def test_prywatna_nazwa_filtru_ZNIKLA():
    """Jeden nosnik znaczy takze jedna NAZWE. Alias zostawiony na zgodnosc
    wstecz jest drugim nosnikiem, ktory nikogo nie boli az do rozjazdu."""
    assert not hasattr(budzet, "_bez_podatkow"), \
        "stara nazwa prywatna zyje dalej — sa dwie drogi do tej samej reguly"


# --- nosnik 2: dzien w miesiacu ------------------------------------------

def test_dzien_MIESZCZACY_sie_w_miesiacu_zostaje_bez_zmian():
    assert terminy.dzien_w_miesiacu(2026, 3, 15) == date(2026, 3, 15)


def test_dzien_31_w_LUTYM_daje_ostatni_dzien_lutego():
    """Regula z `magazyn._wymagaj_dnia`: „rachunek platny 31. trzeba by
    wpisywac dwa razy, raz dla lutego" — az do Z61 nikt jej nie wykonywal."""
    assert terminy.dzien_w_miesiacu(2026, 2, 31) == date(2026, 2, 28)


def test_rok_PRZESTEPNY_daje_29_lutego():
    """Kontrola dwustronna do testu wyzej: „ostatni dzien" liczy sie
    z kalendarza, a nie z zapamietanej 28."""
    assert terminy.dzien_w_miesiacu(2028, 2, 31) == date(2028, 2, 29)


def test_dzien_31_w_miesiacu_30_dniowym_daje_30():
    assert terminy.dzien_w_miesiacu(2026, 4, 31) == date(2026, 4, 30)


def test_dzien_ROWNY_dlugosci_miesiaca_NIE_jest_przesuwany():
    """Kontrola dwustronna: przesuniecie „o jeden za daleko" na krancu
    zakresu wygladalo by identycznie jak dzialajaca regula."""
    assert terminy.dzien_w_miesiacu(2026, 4, 30) == date(2026, 4, 30)
    assert terminy.dzien_w_miesiacu(2026, 12, 31) == date(2026, 12, 31)


def test_dzien_SPOZA_zakresu_jest_bledem():
    """Zero i 32 to nie „dzien do przyciecia", tylko wpis, ktorego magazyn
    nigdy nie przyjal. Ciche przyciecie zamienilo by blad w liczbe."""
    for zly in (0, 32, -1):
        with pytest.raises(ValueError):
            terminy.dzien_w_miesiacu(2026, 5, zly)


def test_ZGODA_dwoch_nosnikow_dnia_na_krancu_zakresu():
    """Straznik odlozonej konsolidacji (CLAUDE.md §8 v1.17).

    Zakres dnia ma DWA nosniki: `magazyn._wymagaj_dnia` sprawdza go przy
    zapisie, `terminy.dzien_w_miesiacu` rozwiazuje przy odczycie. To dwie
    rozne reguly, ale dziela kraniec zakresu — i gdyby sie rozjechaly, wpis
    przyjety przez magazyn wysypal by prognoze albo odwrotnie.

    **Prog konsolidacji: przy pierwszej zmianie zakresu dnia w ktorymkolwiek
    z tych dwoch miejsc.**
    """
    rozwiazane = 0
    for miesiac in range(1, 13):
        for dzien in range(1, 32):
            assert magazyn._wymagaj_dnia(dzien) == dzien
            wynik = terminy.dzien_w_miesiacu(2026, miesiac, dzien)
            assert wynik.month == miesiac
            rozwiazane += 1
    assert rozwiazane == 12 * 31, \
        f"kontrola licznosci: rozwiazano {rozwiazane} dni, nie 372"

    with pytest.raises(magazyn.BladMagazynu):
        magazyn._wymagaj_dnia(32)
    with pytest.raises(ValueError):
        terminy.dzien_w_miesiacu(2026, 5, 32)
