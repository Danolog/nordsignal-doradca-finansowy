"""Kotwica prognozy — stan konta z historia (Z60, zdolnosc E7).

Dlaczego TABELA Z HISTORIA, a nie klucz w `ustawienia` (plan Z60):
kotwica jest jedyna liczba decydujaca o tym, czy cala prognoza jest prawdziwa.
Gdy sie pomyli, pierwsze pytanie brzmi „jaka byla kotwica, kiedy to mowila" —
nadpisany klucz nie odpowie. Drugi zysk: kotwica z 1 sierpnia + prognoza na
1 wrzesnia + kotwica z 1 wrzesnia to JEDYNY sposob, w jaki ta prognoza moze
kiedykolwiek udowodnic, ze jest skalibrowana.

Kwota kotwicy MOZE byc ujemna — to jedyna kwota w tej bazie, ktora moze.
Konto na debecie jest realnym stanem, a `_wymagaj_nieujemnej` (wpisy, kapital,
rata) broni czego innego: tam kierunek niesie TYP pozycji, tu znak jest
czescia odczytu z banku.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from silnik.rdzen import budzet, magazyn
from testy import pomocnicze


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz()
    yield polaczenie
    polaczenie.close()


def _baza_w_wersji(wersja: int) -> None:
    """Realna baza z danymi, ostemplowana podana wersja schematu."""
    magazyn.zmigruj_i_polacz().close()
    surowe = pomocnicze.polaczenie_surowe()
    surowe.execute(
        "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, szczegoly) "
        "VALUES ('2026-08-01', %s, 'Zakupy', 10.00, '')",
        (budzet.TYP_WYDATKI,))
    surowe.execute("DROP TABLE IF EXISTS stan_konta")
    surowe.execute("UPDATE wersja_schematu SET wersja = %s", (wersja,))
    surowe.commit()
    surowe.close()


# --- kwota wraca co do grosza --------------------------------------------

def test_zapisana_kotwica_WRACA_co_do_grosza_jako_Decimal(p):
    """Kryterium odbioru. Grosze gubi `float`, a to jest liczba, od ktorej
    zalezy odpowiedz „czy w listopadzie zejde ponizej zera"."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 8, 27),
                              kwota=Decimal("12345.67"))

    kotwice = magazyn.wczytaj_kotwice(p)
    assert len(kotwice) == 1, f"kotwic jest {len(kotwice)}, nie jedna"
    kwota = kotwice.iloc[0]["kwota"]
    assert isinstance(kwota, Decimal), \
        f"kwota wrocila jako {type(kwota).__name__}, nie Decimal"
    assert kwota == Decimal("12345.67")
    assert kotwice.iloc[0]["data"] == date(2026, 8, 27)


def test_kotwica_UJEMNA_jest_dopuszczalna(p):
    """Konto na debecie to realny stan konta, nie blad wpisu. To jedyna
    kwota w tej bazie, ktora moze byc ujemna."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 8, 27),
                              kwota=Decimal("-1840.55"))
    assert magazyn.wczytaj_kotwice(p).iloc[0]["kwota"] == Decimal("-1840.55")


def test_kwota_NIE_bedaca_liczba_jest_bledem(p):
    """Kontrola dwustronna do testu wyzej: brak walidacji znaku nie znaczy
    braku walidacji. Napis zapisany jako kwota wroci przez `_KWOTOWE`
    i wysypie sie dopiero przy liczeniu, czyli daleko od miejsca wpadki."""
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_stan_konta(p, data=date(2026, 8, 27), kwota="dwa tysiace")
    assert "kwot" in str(blad.value).lower()


# --- historia zostaje ----------------------------------------------------

def test_HISTORIA_zostaje_zamiast_byc_nadpisana(p):
    """Sedno decyzji z planu Z60. Trzy odczyty z trzech dni to trzy wiersze —
    inaczej nie da sie sprawdzic, czy prognoza sprzed miesiaca trafila."""
    for dzien, kwota in ((1, "5000.00"), (15, "3200.10"), (27, "1840.55")):
        magazyn.zapisz_stan_konta(p, data=date(2026, 8, dzien),
                                  kwota=Decimal(kwota))

    kotwice = magazyn.wczytaj_kotwice(p)
    assert len(kotwice) == 3, f"historia ma {len(kotwice)} wierszy, nie trzy"
    # Bez kolejnosci swiadomie: kolejnosci pilnuje osobny straznik nizej,
    # zeby jedna mutacja czerwienila dokladnie jeden test.
    assert sorted(kotwice["kwota"]) == [Decimal("1840.55"), Decimal("3200.10"),
                                        Decimal("5000.00")]


def test_kotwice_wracaja_od_NAJNOWSZEJ(p):
    """Kolejnosc jest regula, nie wygoda: pierwszy wiersz to kotwica
    obowiazujaca. Gdyby wracaly od najstarszej, prognoza wystartowalaby
    ze stanu sprzed miesiaca i wygladalaby na policzona."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 7, 1), kwota=Decimal("100.00"))
    magazyn.zapisz_stan_konta(p, data=date(2026, 9, 1), kwota=Decimal("300.00"))
    magazyn.zapisz_stan_konta(p, data=date(2026, 8, 1), kwota=Decimal("200.00"))

    # Obiekty daty, nie napisy: kolumna jest typu `DATE` (W4). Sortowanie
    # idzie odtad po DACIE, a nie po zapisie tekstowym — dla formatu ISO
    # wynik jest ten sam, ale dla kazdego innego juz nie.
    assert list(magazyn.wczytaj_kotwice(p)["data"]) \
        == [date(2026, 9, 1), date(2026, 8, 1), date(2026, 7, 1)]


def test_ta_sama_DATA_poprawia_odczyt_zamiast_go_dublowac(p):
    """Dwa stany konta na ten sam dzien to nie historia, tylko sprzecznosc —
    poprawka literowki ma nadpisac, nie dolozyc drugiej prawdy."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 8, 27), kwota=Decimal("999.99"))
    magazyn.zapisz_stan_konta(p, data=date(2026, 8, 27), kwota=Decimal("1840.55"))

    kotwice = magazyn.wczytaj_kotwice(p)
    assert len(kotwice) == 1, "poprawka odczytu zdublowala wiersz"
    assert kotwice.iloc[0]["kwota"] == Decimal("1840.55")


def test_brak_kotwicy_daje_PUSTA_historie_a_nie_blad(p):
    """Brak kotwicy to normalny stan poczatkowy — prognoza ma z niego zrobic
    „nie wiem" (R11), a nie wyjatek na starcie aplikacji."""
    kotwice = magazyn.wczytaj_kotwice(p)
    assert len(kotwice) == 0
    assert "kwota" in kotwice.columns, \
        "pusta ramka bez kolumn wysypie kazdego konsumenta"


# --- migracja 8 -> 9 (cwiczy Z53) ----------------------------------------

def test_migracja_z_OSEMKI_doklada_tabele_i_ZOSTAWIA_kopie(tmp_path):
    """Kryterium odbioru Z60: pierwsza migracja schematu po Z53 w plasterku 1.

    Sprawdzane sa trzy rzeczy naraz, bo awaria kazdej z nich wyglada tak
    samo — jak dzialajaca aplikacja: tabela powstaje w bazie, ktora juz ma
    dane; kopia sprzed migracji istnieje i jest w wersji 8; dane przezyly.
    """
    _baza_w_wersji(8)

    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_stan_konta(polaczenie, data=date(2026, 8, 27),
                              kwota=Decimal("1840.55"))
    assert polaczenie.execute(
        "SELECT wersja FROM wersja_schematu WHERE jedyny").fetchone()[0] \
        == magazyn.WERSJA_SCHEMATU
    assert polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 1, \
        "migracja zgubila dane sprzed niej"

    kopie = magazyn.kopie(polaczenie)
    assert len(kopie) == 1, f"kopii jest {len(kopie)}, nie jedna (Z53)"
    assert polaczenie.execute(
        f"SELECT wersja FROM {kopie[0]}.wersja_schematu").fetchone()[0] == 8
    assert polaczenie.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = %s"
        " AND table_name = 'stan_konta'", (kopie[0],)).fetchone() is None, \
        "kopia ma byc stanem SPRZED migracji"
    polaczenie.close()


def test_wersja_schematu_OBEJMUJE_kotwice_i_stempluje_baze(p):
    """Zmieniony swiadomie w Z71, razem z podniesieniem schematu 9 -> 10.

    Stare brzmienie (Z60): `assert magazyn.WERSJA_SCHEMATU == 9` oraz
    `... == 9`, pod nazwa `test_wersja_schematu_PODNIESIONA_do_dziewiatej`.
    Dokladny numer schematu ma od Z71 JEDEN nosnik —
    `testy/test_straznik.py::test_wersja_schematu_PODNIESIONA_do_dziesiatej`.
    Tutaj zostaje to, co nalezy do kotwicy: tabela weszla w wersji 9, a baza
    jest stemplowana wersja, ktora zna kod (a nie liczba wpisana obok).
    """
    assert magazyn.WERSJA_SCHEMATU >= 9
    assert p.execute(
        "SELECT wersja FROM wersja_schematu WHERE jedyny").fetchone()[0] \
        == magazyn.WERSJA_SCHEMATU
