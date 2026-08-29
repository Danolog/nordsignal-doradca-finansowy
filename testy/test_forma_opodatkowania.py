"""Strazniki formy opodatkowania jako ustawienia PER ROK (Z57, plan Z29).

Trzy stany, nie dwa (decyzja D8). Wartosc domyslna, ktora udaje wybor, jest
gorsza niz brak wartosci: v0.2 planu zakladala ryczalt, v0.3 skale — obie
zgadywaly, tylko w przeciwne strony. Aplikacja formy sprzed zawieszenia
dzialalnosci NIE ZNA i nie ma jej skad wziac.

Precedens we wlasnym kodzie: `weryfikacja.sprawdz` przy wyniku ROZBIEZNE
blokuje formularz faktury, zamiast liczyc z niepewnych stawek. Ta sama zasada,
inne wejscie.

Zaczep migracyjny wpisuje `(2026, SKALA)` jako WPIS wynikajacy z ustalenia §0
planu, nie jako wartosc domyslna kodu. Roznica jest widoczna w zachowaniu:
rok 2027 zostaje pusty i zachowuje sie jak NIEROZSTRZYGNIETA.
"""

import sqlite3

import pytest

from silnik.rdzen import magazyn


@pytest.fixture
def p(tmp_path):
    return magazyn.polacz(tmp_path / "forma.db")


# --- trzy stany -----------------------------------------------------------

def test_brak_wpisu_daje_NIEROZSTRZYGNIETA_a_nie_ryczalt_ani_skale(p):
    """Kryterium odbioru planu Z29. Straznik odwrocony wobec DWOCH kolejnych
    wersji planu: v0.2 zgadywala ryczalt, v0.3 skale."""
    forma = magazyn.forma_na_rok(p, 2030)
    assert forma.forma == magazyn.FORMA_NIEROZSTRZYGNIETA
    assert forma.forma != magazyn.FORMA_RYCZALT
    assert forma.forma != magazyn.FORMA_SKALA
    assert forma.stawka_ryczaltu is None


def test_zaczep_migracyjny_wpisuje_SKALE_na_2026(p):
    """Ustalenie §0 planu: Darek byl na zasadach ogolnych przed zawieszeniem,
    a milczenie do 20.10.2026 utrwala skale. To WPIS, wiec da sie go zmienic
    i da sie zobaczyc, ze istnieje."""
    assert magazyn.forma_na_rok(p, 2026).forma == magazyn.FORMA_SKALA
    wiersze = p.execute(
        "SELECT rok, forma FROM forma_opodatkowania ORDER BY rok").fetchall()
    assert wiersze == [(2026, magazyn.FORMA_SKALA)], \
        f"zaczep wpisal cos innego niz jeden wiersz: {wiersze}"


def test_rok_2027_zostaje_PUSTY_bo_wpis_to_nie_wartosc_domyslna(p):
    """To jest cala roznica miedzy wpisem a wartoscia domyslna, i jest ona
    WIDOCZNA W ZACHOWANIU — nie tylko w komentarzu."""
    assert magazyn.forma_na_rok(p, 2027).forma == magazyn.FORMA_NIEROZSTRZYGNIETA


# --- zapis ----------------------------------------------------------------

def test_zapis_formy_WRACA_przy_odczycie(p):
    magazyn.zapisz_forme(p, rok=2027, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu="0.085")
    forma = magazyn.forma_na_rok(p, 2027)
    assert forma.forma == magazyn.FORMA_RYCZALT
    assert str(forma.stawka_ryczaltu) == "0.085"


def test_zmiana_formy_na_2027_NIE_RUSZA_2026(p):
    """Kryterium odbioru planu Z29. Powod, dla ktorego to osobna tabela,
    a nie klucz w `ustawienia`: tamta nie ma wymiaru roku."""
    magazyn.zapisz_forme(p, rok=2027, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu="0.085")
    assert magazyn.forma_na_rok(p, 2026).forma == magazyn.FORMA_SKALA
    assert magazyn.forma_na_rok(p, 2027).forma == magazyn.FORMA_RYCZALT


def test_zapis_NADPISUJE_ten_sam_rok(p):
    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu="0.085")
    assert magazyn.forma_na_rok(p, 2026).forma == magazyn.FORMA_RYCZALT
    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_SKALA)
    assert magazyn.forma_na_rok(p, 2026).forma == magazyn.FORMA_SKALA
    assert magazyn.forma_na_rok(p, 2026).stawka_ryczaltu is None


# --- bledy zamiast cichych zer --------------------------------------------

def test_forma_SPOZA_ZBIORU_jest_bledem_przy_zapisie(p):
    """Kryterium odbioru planu Z29. Cichy zapis nieznanej formy dalby stan,
    ktorego silnik nie umie obsluzyc — i wyszlo by to dopiero przy liczeniu."""
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_forme(p, rok=2027, forma="LINIOWY")
    assert "LINIOWY" in str(blad.value)


def test_NIEROZSTRZYGNIETA_nie_da_sie_ZAPISAC(p):
    """To stan ODCZYTU (brak wpisu), nie wartosc do wpisania. Zapisanie go
    utworzyloby wiersz znaczacy „swiadomie nie wiem", nieodrozniamy przy
    odczycie od braku wiersza — czyli drugi nosnik jednego stanu."""
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_forme(p, rok=2027,
                             forma=magazyn.FORMA_NIEROZSTRZYGNIETA)


def test_RYCZALT_BEZ_stawki_jest_bledem(p):
    """Ryczalt bez stawki to forma, ktorej nie da sie policzyc."""
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_forme(p, rok=2027, forma=magazyn.FORMA_RYCZALT)
    assert "stawk" in str(blad.value).lower()


def test_SKALA_ZE_stawka_ryczaltu_jest_bledem(p):
    """Kontrola dwustronna: stawka ryczaltu przy skali to pole, ktore ktos
    pozniej przeczyta i uzna za obowiazujace."""
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_forme(p, rok=2027, forma=magazyn.FORMA_SKALA,
                             stawka_ryczaltu="0.085")


def test_wpis_USZKODZONY_w_bazie_jest_bledem_przy_odczycie(p):
    """Wiersz z forma spoza zbioru mogl powstac przed dolozeniem walidacji
    albo recznie. Cichy powrot NIEROZSTRZYGNIETA zamienilby „mam zla forme"
    w „nie mam formy" — dwa rozne stany pod jedna odpowiedzia.

    ZMIANA W1 (2026-08-29): od dolozenia wiezu `forma_znana` do `_SCHEMAT`
    baza SWIEZA takiego wiersza nie wpusci — i to jest cel, nie przeszkoda.
    Ale wiez dostaje wylacznie baza swieza (`CREATE TABLE IF NOT EXISTS` nie
    rusza tabeli, ktora juz jest, a `ALTER TABLE` w SQLite nie dolozy
    `CHECK`), wiec baza ROBOCZA Darka nadal moze taki wiersz niesc. Ta
    sciezka musi zostac sprawdzona — `PRAGMA ignore_check_constraints`
    odtwarza ksztalt bazy bez wiezu na czas samego wstawienia.
    Odczyt idzie juz normalnie, z wiezem wlaczonym z powrotem.
    """
    p.execute("PRAGMA ignore_check_constraints = ON")
    p.execute("INSERT INTO forma_opodatkowania (rok, forma) VALUES (2029, ?)",
              ("KARTA_PODATKOWA",))
    p.commit()
    p.execute("PRAGMA ignore_check_constraints = OFF")
    assert p.execute(
        "SELECT forma FROM forma_opodatkowania WHERE rok = 2029"
    ).fetchone()[0] == "KARTA_PODATKOWA", (
        "wiersz uszkodzony nie wszedl do bazy — test nie sprawdzilby niczego")
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.forma_na_rok(p, 2029)
    assert "KARTA_PODATKOWA" in str(blad.value)


# --- schemat --------------------------------------------------------------

def test_wersja_schematu_OBEJMUJE_forme_i_stempluje_baze(p):
    """Zmieniony swiadomie w Z60, razem z podniesieniem schematu 8 -> 9.

    Stare brzmienie (Z57): `assert magazyn.WERSJA_SCHEMATU == 8` oraz
    `... == 8`. Dokladny numer schematu ma od Z60 JEDEN nosnik —
    `testy/test_stan_konta.py::test_wersja_schematu_PODNIESIONA_do_dziewiatej`.
    Tutaj zostaje to, co nalezy do formy: tabela weszla w wersji 8, a baza
    jest stemplowana wersja, ktora zna kod (a nie liczba wpisana obok).
    """
    assert magazyn.WERSJA_SCHEMATU >= 8
    assert p.execute("PRAGMA user_version").fetchone()[0] \
        == magazyn.WERSJA_SCHEMATU


def test_migracja_z_siodemki_TWORZY_tabele_i_wpis(tmp_path):
    """Pierwsza migracja cwiczaca Z53. Baza w wersji 7 bez tabeli formy —
    dokladnie stan produkcyjny Darka przed tym zadaniem."""
    sciezka = tmp_path / "stara.db"
    magazyn.polacz(sciezka).close()
    surowe = sqlite3.connect(str(sciezka))
    surowe.execute("DROP TABLE forma_opodatkowania")
    surowe.execute("PRAGMA user_version = 7")
    surowe.commit()
    surowe.close()

    polaczenie = magazyn.polacz(sciezka)
    assert magazyn.forma_na_rok(polaczenie, 2026).forma == magazyn.FORMA_SKALA
    assert polaczenie.execute("PRAGMA user_version").fetchone()[0] \
        == magazyn.WERSJA_SCHEMATU
    polaczenie.close()

    kopie = sorted(tmp_path.glob("*-kopia-przed-migracja-*"))
    assert len(kopie) == 1, "migracja schematu ma zostawic kopie (Z53)"


def test_zaczep_NIE_nadpisuje_istniejacego_wyboru(tmp_path):
    """Gdyby zaczep wpisywal przy kazdym otwarciu, zmiana formy na 2026
    cofalaby sie po restarcie aplikacji — i wygladalo by to jak niezapisany
    formularz."""
    sciezka = tmp_path / "wybor.db"
    pierwsze = magazyn.polacz(sciezka)
    magazyn.zapisz_forme(pierwsze, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu="0.085")
    pierwsze.close()

    drugie = magazyn.polacz(sciezka)
    assert magazyn.forma_na_rok(drugie, 2026).forma == magazyn.FORMA_RYCZALT
    drugie.close()
