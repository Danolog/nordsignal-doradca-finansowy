# -*- coding: utf-8 -*-
"""Strazniki wskazania bazy zmienna srodowiskowa `DATABASE_URL`.

NASTEPCA `test_sciezka_bazy.py` (Z52 -> W4, 2026-08-29). Powod istnienia
zadania sie nie zmienil: mandat „agenty pracuja bez udzialu Darka" stoi na
warunku „agenty pracuja na kopii, nigdy na bazie roboczej". Zmienil sie
przedmiot: baza nie jest juz PLIKIEM, tylko ADRESEM POLACZENIA.

TRYB AWARII, PRZED KTORYM TO BRONI, brzmi tak samo: „patrzylem w niewlasciwa
baze i wygladalo dobrze". Dlatego samo wskazanie nie wystarcza — rozwiazany
adres musi byc WIDOCZNY, a pod pytestem adres spoza bazy testowej musi byc
BLEDEM.

CO OSLABLO PRZY ZMIANIE PLIKU NA ADRES — pozycja obowiazkowa §3.11, wypisana
tutaj, bo tutaj mieszka straznik:

  * `Path.resolve()` sprowadzalo kazdy zapis sciezki do JEDNEJ postaci:
    `./a/../cfo.db`, `~/cfo.db` i sciezka bezwzgledna byly nie do odroznienia
    dla porownania. Adres polaczenia takiej postaci kanonicznej NIE MA;
  * NASTEPCA CZESCIOWY: adres rozkladamy PARSEREM STEROWNIKA
    (`psycopg.conninfo.conninfo_to_dict`) i porownujemy `host`, `port`
    i `dbname` osobno. To lapie kazdy zapis, ktory sterownik rozumie tak samo
    — w tym inna kolejnosc parametrow i postac `klucz=wartosc` zamiast
    adresu z ukosnikami;
  * CZEGO NIE LAPIE, wprost: dwoch ROZNYCH NAZW tego samego serwera. Tunel
    wystawiony pod inna nazwa na `127.0.0.1` przejdzie jako lokalny, a
    `localhost` przekierowany w `/etc/hosts` na serwer zdalny — takze.
    Sprowadzenie nazwy do adresu sieciowego wymagaloby zapytania do systemu
    nazw przy KAZDYM otwarciu bazy; tego nie robimy;
  * BRAMKA JEST ZA TO SZERSZA W INNYM WYMIARZE. Poprzednik znal dwie zakazane
    sciezki i przepuszczal wszystko inne. Ten straznik dziala odwrotnie:
    przepuszcza WYLACZNIE maszyne lokalna i wylacznie nazwe bazy spoza listy
    baz roboczych. Nowa baza produkcyjna nie musi byc nigdzie dopisana, zeby
    byla chroniona.
"""

import pytest

from silnik.rdzen import magazyn
from testy import conftest as oslony


# --- rozwiazywanie adresu --------------------------------------------------

def test_zmienna_srodowiskowa_WSKAZUJE_baze(monkeypatch):
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY,
                       "postgresql://kto:tajne@localhost:5434/doradca_test")
    assert magazyn.adres_bazy() == \
        "postgresql://kto:tajne@localhost:5434/doradca_test"


def test_brak_zmiennej_jest_ODMOWA_a_nie_zgadywaniem(monkeypatch):
    """Kontrola dwustronna i zarazem zmiana zachowania wobec poprzednika.

    Poprzednik mial wartosc domyslna — plik `cfo_database.db` obok kodu — wiec
    brak zmiennej znaczyl „otworz to, co lezy w repozytorium". Adres zgadniety
    prowadzilby do serwera, ktorego nikt nie wskazal, a wtedy „patrzylem
    w niewlasciwa baze i wygladalo dobrze" wraca tylnymi drzwiami.

    Przez `_rozwiaz_adres`, nie `adres_bazy` — patrz docstring tej funkcji.
    """
    monkeypatch.delenv(magazyn.ZMIENNA_BAZY, raising=False)
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn._rozwiaz_adres()
    assert magazyn.ZMIENNA_BAZY in str(blad.value), \
        "odmowa ma powiedziec, KTORA zmienna ustawic"
    assert "zgadu" in str(blad.value).lower(), \
        "odmowa ma powiedziec, DLACZEGO nie ma wartosci domyslnej"


def test_zmienna_PUSTA_znaczy_brak_zmiennej(monkeypatch):
    """`DATABASE_URL="   "` rozwiazaloby sie na adres pusty, czyli na baze
    wskazana przez zmienne systemowe sterownika — a wiec na baze, ktorej
    nazwy nikt nie podal."""
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, "   ")
    with pytest.raises(magazyn.BladMagazynu):
        magazyn._rozwiaz_adres()


def test_polacz_BEZ_argumentu_idzie_za_zmienna(baza):
    """To jest sedno zadania: warstwa sieciowa wola `polacz()` bez argumentu."""
    magazyn.zmigruj()
    polaczenie = magazyn.polacz()
    try:
        assert magazyn._wersja_bazy(polaczenie) == magazyn.WERSJA_SCHEMATU
    finally:
        polaczenie.close()


def test_argument_WYGRYWA_ze_zmienna(baza, monkeypatch):
    """Parametr zostaje — uzywaja go narzedzia z wiersza polecen."""
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY,
                       "postgresql://nikt@localhost:1/nie-ma-takiej")
    magazyn.zmigruj(baza)
    polaczenie = magazyn.polacz(baza)
    try:
        assert magazyn._wersja_bazy(polaczenie) == magazyn.WERSJA_SCHEMATU
    finally:
        polaczenie.close()


# --- straznik: pod pytestem NIGDY baza spoza testowej ---------------------

def test_pod_pytestem_baza_ROBOCZA_jest_BLEDEM(monkeypatch):
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY,
                       "postgresql://kto@localhost:5434/doradca")
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.adres_bazy()
    assert "doradca" in str(blad.value)
    assert oslony.ZMIENNA_BAZY_TESTOWEJ in str(blad.value), \
        "komunikat ma mowic, co zrobic, nie tylko ze zle"


def test_pod_pytestem_serwer_ZDALNY_jest_BLEDEM(monkeypatch):
    """Wymiar, ktorego poprzednik NIE MIAL: baza produkcyjna nie musi byc
    nigdzie wypisana, zeby byla chroniona — wystarczy, ze nie stoi tutaj."""
    monkeypatch.setenv(
        magazyn.ZMIENNA_BAZY,
        "postgresql://kto:tajne@ep-cos.eu-central-1.aws.neon.tech/doradca_test")
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.adres_bazy()
    assert "neon.tech" in str(blad.value)


def test_straznik_ISTNIEJE_a_nie_tylko_powinien():
    """Kontrola licznosci. Testy wyzej przeszlyby takze wtedy, gdyby bledem
    rzucalo cokolwiek innego — a lista straznikow byla pusta."""
    assert magazyn.STRAZNICY_ADRESU, \
        "conftest.py nie zainstalowal straznika adresu"


def test_straznik_PRZEPUSZCZA_baze_testowa(monkeypatch):
    """Kontrola dwustronna: bramka, ktora blokuje wszystko, nie jest bramka."""
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY,
                       "postgresql://kto@localhost:5434/doradca_test")
    assert magazyn.adres_bazy().endswith("/doradca_test")


@pytest.mark.parametrize("zapis", [
    "postgresql://kto:tajne@localhost:5434/doradca",
    "postgres://kto:tajne@localhost:5434/doradca",
    "host=localhost port=5434 dbname=doradca user=kto password=tajne",
    "dbname=doradca host=localhost",
])
def test_ten_sam_zakaz_dziala_na_KAZDYM_zapisie_adresu(monkeypatch, zapis):
    """Nastepca `Path.resolve()`: rozne zapisy TEGO SAMEGO adresu maja dawac
    ten sam werdykt. Cztery zapisy, jedna odpowiedz."""
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, zapis)
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.adres_bazy()


# --- widocznosc i tajemnica hasla -----------------------------------------

def test_opis_bazy_mowi_ktora_baze_otwarto(monkeypatch):
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY,
                       "postgresql://kto:tajne@localhost:5434/doradca_test")
    opis = magazyn.opis_bazy()
    assert opis.adres == "localhost:5434/doradca_test"
    assert opis.domyslna is False


def test_opis_bazy_przy_serwerze_ZDALNYM_mowi_ze_produkcyjna():
    """Kontrola dwustronna. Adres podany jawnie, bo `opis_bazy()` bez
    argumentu przeszlaby przez bramke — i slusznie."""
    opis = magazyn.opis_bazy(
        "postgresql://kto:tajne@ep-cos.eu-central-1.aws.neon.tech/doradca")
    assert opis.domyslna is True
    assert "neon.tech" in opis.adres


def test_ZADEN_opis_ani_komunikat_NIE_NIESIE_hasla(monkeypatch):
    """CLAUDE.md §8: nigdy wartosc sekretu w dowodzie ani na ekranie.

    Adres bazy niesie haslo do produkcji. Kazde miejsce, ktore pokazuje
    czlowiekowi „ktora baze otwarto", wola `adres_bez_hasla` — ten test
    sprawdza WSZYSTKIE trzy naraz: opis, komunikat odmowy i raport migracji.
    """
    tajne = "haslo-ktorego-nie-wolno-zobaczyc"
    adres = f"postgresql://kto:{tajne}@localhost:5434/doradca_test"
    assert tajne not in magazyn.adres_bez_hasla(adres)
    assert tajne not in magazyn.opis_bazy(adres).adres

    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, adres)
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.polacz()
    assert tajne not in str(blad.value), \
        "komunikat odmowy wypisal haslo do bazy"
    assert "localhost:5434/doradca_test" in str(blad.value), \
        "komunikat ma powiedziec, KTORA baze — bez hasla, ale konkretnie"
