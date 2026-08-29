"""Strazniki edycji i kasowania zobowiazan oraz aktywow (Z43).

Zgloszenie Darka 2026-08-26: „dodalem testowo zobowiazanie i majatek ale nie
moge ich teraz usunac ani edytowac". Wpis, ktorego nie da sie cofnac, zamienia
pomylke w trwaly stan bazy — a ta baza liczy kafelek „Wartosc netto".

Klucz operacji to NUMER wiersza, nie nazwa: dwa kredyty moga nazywac sie tak
samo, a kasowanie po nazwie zabraloby oba.
"""

from decimal import Decimal

import pytest

from silnik.rdzen import magazyn
from testy import pomocnicze


@pytest.fixture
def p(tmp_path):
    return magazyn.zmigruj_i_polacz()


def _zobowiazanie(polaczenie, nazwa="Kredyt Revolut", kapital="43000.00",
                  rata="1300.00") -> int:
    return magazyn.zapisz_zobowiazanie(
        polaczenie, nazwa=nazwa, kapital=Decimal(kapital),
        rata_minimalna=Decimal(rata))


def _aktywo(polaczenie, nazwa="Oszczędności", kategoria="poduszka",
            wartosc="5000.00") -> int:
    return magazyn.zapisz_aktywo(polaczenie, nazwa_aktywa=nazwa,
                                 kategoria=kategoria, wartosc=Decimal(wartosc))


# --- zobowiazania: tylko kapital i rata -----------------------------------

def test_zobowiazanie_niesie_kapital_rate_I_OPROCENTOWANIE(p):
    """SPROSTOWANIE 2026-08-28 (D9) — ten straznik pilnowal decyzji, ktora
    zostala odwrocona przez tego samego czlowieka.

    Brzmienie sprzed zmiany, doslownie: *„Decyzja Darka 2026-08-26:
    »w zobowiazaniach nalezy umiescic tylko kapital do splaty i rata
    miesieczna«. Oprocentowanie nie wchodzilo do zadnej liczby"* — i test
    asertowal `kolumny == {"id","nazwa","kapital","rata_minimalna"}`.

    Darek 2026-08-28 godz. 19:38: „Samo pole — zebym mogl wpisac".
    Oprocentowanie wraca jako POLE DO ZBIERANIA DANYCH; nadal nie wchodzi
    do zadnej liczby i to jest osobno pilnowane w `test_oprocentowanie.py`.
    Testu nie oslabiono — sprawdza teraz KOMPLET kolumn, tak samo scisle.
    """
    kolumny = pomocnicze.kolumny_tabeli(p, "zobowiazania")
    assert kolumny == {"id", "nazwa", "kapital", "rata_minimalna",
                       "oprocentowanie"}


def test_migracja_D9_ZACHOWUJE_oprocentowanie_w_istniejacej_bazie(tmp_path):
    """SPROSTOWANIE 2026-08-28 (D9). Ten test pilnowal migracji Z43, ktora
    KASOWALA kolumne; Darek odwrocil te decyzje, wiec kolumna ma teraz
    PRZEZYC. Brzmienie sprzed zmiany, doslownie: *„Kolumna znika takze
    z bazy, ktora juz jest"*, z asercja `assert "oprocentowanie" not in kolumny`.

    UWAGA O JEDNOSTCE — realne ryzyko, nie teoria. Stara kolumna trzymala
    UlAMEK (`0.0725` = 7,25%), nowa trzyma PROCENT (`9` = 9%). Baza, ktorej
    nikt nie otworzyl od 2026-08-26, ma jeszcze stare wartosci w starej
    jednostce i ta migracja ich NIE PRZELICZA — zachowuje je bez zmian.
    Ten test utrwala to zachowanie jawnie, zeby nikt nie odkryl go zdziwieniem.
    """
    polaczenie = pomocnicze.polaczenie_surowe()
    polaczenie.execute("""
        CREATE TABLE zobowiazania (
            id BIGSERIAL PRIMARY KEY,
            nazwa TEXT NOT NULL, kapital NUMERIC(14,2) NOT NULL,
            oprocentowanie NUMERIC(6,3) NOT NULL,
            rata_minimalna NUMERIC(14,2) NOT NULL
        );
        CREATE TABLE wersja_schematu (
            jedyny BOOLEAN PRIMARY KEY DEFAULT TRUE, wersja INT NOT NULL,
            CONSTRAINT naprawde_jedyny CHECK (jedyny));
    """)
    polaczenie.execute(
        "INSERT INTO zobowiazania (nazwa, kapital, oprocentowanie, "
        "rata_minimalna) VALUES ('Kredyt Revolut',43000.00,0.073,1300.00)")
    polaczenie.execute(
        "INSERT INTO wersja_schematu (jedyny, wersja) VALUES (TRUE, 5)")
    polaczenie.commit()
    polaczenie.close()

    nowe = magazyn.zmigruj_i_polacz()
    kolumny = pomocnicze.kolumny_tabeli(nowe, "zobowiazania")
    assert "oprocentowanie" in kolumny, \
        "kolumna ma PRZEZYC migracje — inaczej wartosc Darka ginie przy starcie"
    # Kontrola licznosci: wiersz przezyl migracje z nietknietymi kwotami.
    assert nowe.execute("SELECT nazwa, kapital, rata_minimalna "
                        "FROM zobowiazania").fetchall() == \
        [("Kredyt Revolut", Decimal("43000.00"), Decimal("1300.00"))]
    # Stara wartosc zostaje NIETKNIETA, w starej jednostce (ulamek).
    # SPROSTOWANIE W4: kolumna ma dzis skale trzech miejsc po przecinku
    # (`NUMERIC(6,3)`), bo trzyma PROCENT, nie ulamek. Wartosc 0,0725 zapisana
    # w starej jednostce zostaje w niej zaokraglona do 0,073 — i to jest
    # DOKLADNIE ten sam rodzaj rozjazdu, przed ktorym ostrzega nagłowek:
    # liczba w cudzej jednostce nie przezyje zmiany typu bez straty.
    assert nowe.execute("SELECT oprocentowanie FROM zobowiazania").fetchone() \
        == (Decimal("0.073"),)


# --- kasowanie ------------------------------------------------------------

def test_usun_zobowiazanie_kasuje_wskazany_wiersz(p):
    numer = _zobowiazanie(p)
    _zobowiazanie(p, nazwa="Karta kredytowa", kapital="2000.00", rata="100.00")
    magazyn.usun_zobowiazanie(p, zobowiazanie_id=numer)
    pozostale = magazyn.wczytaj_zobowiazania(p)
    # Kontrola licznosci: zostaje DOKLADNIE ten drugi, nie „cos zostalo".
    assert list(pozostale["nazwa"]) == ["Karta kredytowa"]


def test_usun_zobowiazanie_nieistniejace_jest_bledem_a_nie_cisza(p):
    """Cisza przy pomylce w numerze wyglada jak sukces — precedens `usun_plan`."""
    with pytest.raises(magazyn.BladMagazynu, match="99"):
        magazyn.usun_zobowiazanie(p, zobowiazanie_id=99)


def test_usun_aktywo_kasuje_wskazany_wiersz(p):
    numer = _aktywo(p)
    _aktywo(p, nazwa="ETF świat", kategoria="ETF", wartosc="12000.00")
    magazyn.usun_aktywo(p, aktywo_id=numer)
    assert list(magazyn.wczytaj_majatek(p)["nazwa_aktywa"]) == ["ETF świat"]


def test_usun_aktywo_nieistniejace_jest_bledem_a_nie_cisza(p):
    with pytest.raises(magazyn.BladMagazynu, match="99"):
        magazyn.usun_aktywo(p, aktywo_id=99)


# --- edycja ---------------------------------------------------------------

def test_zmien_zobowiazanie_poprawia_wszystkie_trzy_pola(p):
    numer = _zobowiazanie(p)
    magazyn.zmien_zobowiazanie(p, zobowiazanie_id=numer, nazwa="Kredyt hipoteczny",
                               kapital=Decimal("320000.00"),
                               rata_minimalna=Decimal("2180.00"))
    w = magazyn.wczytaj_zobowiazania(p).iloc[0]
    assert (w["nazwa"], w["kapital"], w["rata_minimalna"]) == \
        ("Kredyt hipoteczny", Decimal("320000.00"), Decimal("2180.00"))


def test_zmien_zobowiazanie_nie_rusza_pozostalych_wierszy(p):
    """Kontrola licznosci po drugiej stronie: poprawka jednego wiersza nie
    ma prawa dotknac drugiego."""
    numer = _zobowiazanie(p)
    _zobowiazanie(p, nazwa="Karta kredytowa", kapital="2000.00", rata="100.00")
    magazyn.zmien_zobowiazanie(p, zobowiazanie_id=numer, nazwa="Kredyt Revolut",
                               kapital=Decimal("40000.00"),
                               rata_minimalna=Decimal("1300.00"))
    druga = magazyn.wczytaj_zobowiazania(p).iloc[1]
    assert druga["kapital"] == Decimal("2000.00")


def test_zmien_zobowiazanie_nieistniejace_jest_bledem(p):
    with pytest.raises(magazyn.BladMagazynu, match="99"):
        magazyn.zmien_zobowiazanie(p, zobowiazanie_id=99, nazwa="x",
                                   kapital=Decimal("1"),
                                   rata_minimalna=Decimal("1"))


def test_zmien_aktywo_poprawia_nazwe_kategorie_i_wartosc(p):
    numer = _aktywo(p)
    magazyn.zmien_aktywo(p, aktywo_id=numer, nazwa_aktywa="Konto oszczędnościowe",
                         kategoria="lokata", wartosc=Decimal("7500.00"))
    w = magazyn.wczytaj_majatek(p).iloc[0]
    assert (w["nazwa_aktywa"], w["kategoria"], w["wartosc"]) == \
        ("Konto oszczędnościowe", "lokata", Decimal("7500.00"))


def test_zmien_aktywo_nieistniejace_jest_bledem(p):
    with pytest.raises(magazyn.BladMagazynu, match="99"):
        magazyn.zmien_aktywo(p, aktywo_id=99, nazwa_aktywa="x",
                             kategoria="inne", wartosc=Decimal("1"))


def test_kwota_ujemna_zobowiazania_jest_odrzucana(p):
    """Kierunek wynika z rodzaju pozycji, nie ze znaku liczby — ta sama regula
    co przy wpisach budzetu (`zapisz_wpis`)."""
    with pytest.raises(magazyn.BladMagazynu, match="ujemn"):
        _zobowiazanie(p, kapital="-100.00")


def test_kwota_ujemna_aktywa_jest_odrzucana(p):
    with pytest.raises(magazyn.BladMagazynu, match="ujemn"):
        _aktywo(p, wartosc="-100.00")


# --- interfejs: strazniki zrodlowe — NIEPRZENIESIONE, i to jest decyzja ----
#
# W poprzedniku stalo tu SZESC strażnikow czytajacych `pulpit/zobowiazania.py`
# — zakladke starego interfejsu NiceGUI. Nie przenosza sie, bo `pulpit/` jest
# wygaszany razem z cala stara aplikacja (PRD rozdz. 15) i nie ma odpowiednika
# w tym projekcie: nowy interfejs to `interfejs/`, a jego strazniki pisze
# wykonawca ekranu.
#
# CO PRZEZ TO PRZESTAJE DZIALAC — pozycja obowiazkowa, nie retoryczna:
# nikt nie pilnuje juz, ze kosz na liscie zobowiazan wola operacje KASOWANIA,
# a okno dialogowe operacje ZAPISU. W poprzedniku pilnowal tego straznik
# zrodlowy. W tym projekcie ta reguła wraca dopiero z ekranem Majatek, razem
# z jego wlasnym strażnikiem. Do tego czasu jest NIEPILNOWANA — jawnie.
#
# Zostaje w `../AI CFO/testy/test_zobowiazania_majatek.py` i tam nadal dziala.
