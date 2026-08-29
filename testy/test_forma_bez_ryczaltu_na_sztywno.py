"""Straznik: PRZY SKALI ZADNA sciezka aplikacji nie wola silnika ryczaltu.

Siostrzany plik do `test_forma_bez_domyslnej.py`. Tamten pilnuje, ze forma
nie ma WARTOSCI DOMYSLNEJ w `rdzen/podatki.py`; ten pilnuje pieciu miejsc,
w ktorych ryczalt byl ZASZYTY NA SZTYWNO — a wiec omijal tamta bramke, bo
formy nie pomijal, tylko jej nie pytal.

PIEC MIEJSC (stan przed naprawa, 2026-08-28):
  1. `rdzen/doradca.py:51`    — instrukcja systemowa twierdzila modelowi,
     ze uzytkownik rozlicza sie ryczaltem;
  2. `rdzen/narzedzia.py:159` — narzedzie `policz_podatek` bralo stawke
     ryczaltu OD MODELU i wolalo `policz_ryczalt` bezwarunkowo;
  3. `pulpit/jdg.py:117`      — pole „Stawka ryczaltu" w formularzu faktury,
     widoczne niezaleznie od formy, z wartoscia domyslna 8,5%;
  4. `pulpit/jdg.py:153`      — `policz_ryczalt` przy kazdym zapisie faktury;
  5. `pulpit/jdg.py:59`       — kolumna „Ryczalt" w tabeli historii faktur.

Miejsce piate NIE BYLO w zleceniu. Nosnikiem, ktory je niosl, jest naglowek
`testy/test_forma_bez_domyslnej.py` — sekcja „CZEGO TE TESTY NIE PILNUJA".
Odczytany PRZED pomiarem (CLAUDE.md sekcja 8, v1.18: najpierw nosnik).

CZEGO TEN PLIK PILNUJE ZACHOWANIEM, NIE NAPISEM. Wyszukiwanie slowa
„ryczalt" w kodzie nie jest strazikiem: dwie linie niosly kwoty ryczaltowe
bez tego slowa, a kazdy komentarz wyjasniajacy naprawe zawiera je nadal.
Dlatego tutaj `podatki.policz_ryczalt` jest PODMIENIANY na funkcje, ktora
wybucha przy wywolaniu — i sciezka jest przechodzona naprawde.

KONTROLA LICZNOSCI. Pomiar na pustym zbiorze melduje sukces: gdyby ktoras
sciezka przestala byc przechodzona (bo zmienila nazwe, bo test ja cicho
pomija), „zaden wybuch" bylby zielony i falszywy. Dlatego kazde przejscie
dopisuje sie do licznika, a osobny test zada DOKLADNIE PIECIU.
"""

from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import doradca, magazyn, narzedzia, podatki

STAWKA_VAT = Decimal("0.23")
NETTO = Decimal("11200.00")
DZIEN = date(2026, 10, 5)
ROK = DZIEN.year


class WybuchRyczaltu(BaseException):
    """Dziedziczy z `BaseException` — SWIADOMIE.

    Sciezki produkcyjne lapia `Exception` i zamieniaja awarie na uprzejmy
    komunikat na ekranie. Wyjatek dziedziczacy z `Exception` zostalby wiec
    POLKNIETY, test dostalby grzeczny komunikat i zameldowal sukces. Ten sam
    wzorzec, co `BladWyjsciaDoSieci` w `conftest.py`.
    """


def _wybuchowy(*_a, **_k):
    raise WybuchRyczaltu(
        "policz_ryczalt zawolany przy formie SKALA — to jest ta wada.")


@pytest.fixture
def baza_skala(tmp_path):
    """Baza z forma SKALA na rok faktury i jedna faktura w historii."""
    p = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_forme(p, rok=ROK, forma=magazyn.FORMA_SKALA)
    magazyn.zapisz_fakture(
        p, data=date(ROK, 9, 30), numer_faktury="FV/1/2026",
        kwota_netto=NETTO, stawka_vat=STAWKA_VAT, kwota_vat=Decimal("2576.00"),
        pkwiu="74.90.19.0", stawka_ryczaltu=Decimal("0"),
        zaplacony_zus=Decimal("2425.11"), zysk_netto=Decimal("8007.89"),
        stawki_wersja="2026-08-25")
    return p


@pytest.fixture
def baza_ryczalt(tmp_path):
    """Ta sama baza, ale forma RYCZALT — kontrola dwustronna.

    Faktura w historii jest WARUNKIEM POMIARU, nie ozdoba: bez niej ekran
    rysuje zdanie „Brak faktur" zamiast tabeli, a pomiar kolumn dostaje pusty
    zbior i melduje sukces bez ogladania czegokolwiek.
    """
    p = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_forme(p, rok=ROK, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu=Decimal("0.085"))
    magazyn.zapisz_fakture(
        p, data=date(ROK, 9, 30), numer_faktury="FV/1/2026",
        kwota_netto=NETTO, stawka_vat=STAWKA_VAT, kwota_vat=Decimal("2576.00"),
        pkwiu="74.90.19.0", stawka_ryczaltu=Decimal("0.085"),
        zaplacony_zus=Decimal("2425.11"), zysk_netto=Decimal("8007.89"),
        stawki_wersja="2026-08-25")
    return p


# --- (a) ZADNA sciezka nie wola silnika ryczaltu przy SKALI ---------------
#
# Licznik zbiera nazwy sciezek, ktore test FAKTYCZNIE przeszedl. Modul-owy,
# bo kontrola licznosci nizej pyta o komplet, a nie o jedna sciezke.
PRZESZLE: set[str] = set()


def test_sciezka_1_instrukcja_doradcy_nie_twierdzi_ryczaltu(baza_skala):
    """Instrukcja systemowa czyta forme z BAZY, nie ze stalej.

    Tu podmiana silnika nic nie da — ta sciezka nie liczy, tylko MOWI.
    Dowodem jest wiec tresc: instrukcja przy skali nie moze niesc zdania
    o rozliczaniu ryczaltem.
    """
    tekst = doradca.instrukcja_systemowa(baza_skala, dzis=DZIEN)
    assert "skali podatkowej" in tekst, tekst[:200]
    assert "ryczalt" not in tekst.lower().replace("ł", "l"), (
        "instrukcja twierdzi ryczalt komus na skali")
    PRZESZLE.add("doradca.instrukcja_systemowa")


def test_sciezka_2_narzedzie_doradcy_nie_wola_ryczaltu(baza_skala, monkeypatch):
    """Narzedzie `policz_podatek` liczy forma z bazy i NIE bierze stawki."""
    monkeypatch.setattr(podatki, "policz_ryczalt", _wybuchowy)
    n = narzedzia.zbuduj(baza_skala)["policz_podatek"]
    wynik = n(kwota_netto=str(NETTO))          # wybuchnie, jesli wola ryczalt
    assert wynik["nazwa_podatku"] == "PIT", wynik["nazwa_podatku"]
    assert "podstawa_ryczaltu" not in wynik, (
        "wynik dla skali niesie pojecie ryczaltu")
    PRZESZLE.add("narzedzia.policz_podatek")


def test_sciezka_2b_narzedzie_nie_przyjmuje_stawki_ryczaltu(baza_skala):
    """Model nie ma JAK podac stawki ryczaltu — parametru nie ma w sygnaturze.

    Zabezpieczenie strukturalne, nie regulaminowe: dopoki parametr istnial,
    model mogl go podac, a narzedzie policzylo ryczaltem bez pytania o forme.
    """
    n = narzedzia.zbuduj(baza_skala)["policz_podatek"]
    with pytest.raises(TypeError):
        n(kwota_netto=str(NETTO), stawka_ryczaltu="0.085")
    PRZESZLE.add("narzedzia.policz_podatek/sygnatura")


def test_sciezka_3_silnik_faktury_z_bazy_nie_wola_ryczaltu(baza_skala,
                                                           monkeypatch):
    """Sciezka formularza faktury (`pulpit/jdg.py`) — jej rachunek.

    Ekran wola dokladnie te funkcje i nie liczy nic sam; podmiana silnika
    ryczaltu jest wiec pomiarem TEJ sciezki, nie jej atrapy.
    """
    monkeypatch.setattr(podatki, "policz_ryczalt", _wybuchowy)
    forma, w = podatki.policz_fakture_z_bazy(
        baza_skala, kwota_netto=NETTO, stawka_vat=STAWKA_VAT, dzien=DZIEN)
    assert forma.forma == magazyn.FORMA_SKALA
    assert isinstance(w, podatki.WyliczenieSkali), type(w).__name__
    PRZESZLE.add("podatki.policz_fakture_z_bazy")


# --- SCIEZKA 4 (ekran) — NIEPRZENIESIONA ----------------------------------
#
# W poprzedniku stal tu pomiar na WYRENDEROWANYM ekranie `pulpit/jdg.py`:
# budowal zakladke NiceGUI bez serwera i sprawdzal, ze przy skali znika pole
# „Stawka ryczaltu" i kolumna „Ryczalt". Nie przenosi sie — `pulpit/` jest
# wygaszany, a nowy interfejs nie ma jeszcze ekranu Firma.
#
# CO PRZEZ TO PRZESTAJE DZIALAC: przy skali NIKT NIE PILNUJE, ze interfejs nie
# pokazuje pola stawki ryczaltu ani kolumny ryczaltu. Sciezki 1-3 (instrukcja
# doradcy, narzedzie doradcy, silnik faktury) sa pilnowane dalej — niepilnowana
# jest wylacznie WIDOCZNOSC na ekranie. Wraca jako wymog do ekranu Firma,
# razem z pomiarem na wyrenderowanym ekranie, nie na tekscie pliku.
#
# LICZBA SCIEZEK W KONTROLI LICZNOSCI NIZEJ ZESZLA Z PIECIU NA CZTERY
# SWIADOMIE. Zmniejszenie oczekiwanego zbioru bez tej notatki byloby
# rozbrojeniem straznika pod pozorem przenosin.

def test_kontrola_licznosci_cztery_sciezki_przeszly():
    """Ile sciezek pomiar NAPRAWDE zobaczyl (CZTERY po przenosinach —
    piata, ekranowa, opisana wyzej). Zero = czerwien, nie sukces.

    Ten test jest osobny i celowo zalezny od pozostalych: bez niego usuniecie
    dowolnego testu wyzej przeszlo by niezauwazone, a suita nadal byla by
    zielona. Uruchamiany pojedynczo (`-k kontrola_licznosci`) pada — to jest
    poprawne zachowanie, nie wada: pomiar bez przejsc NIE MA czego meldowac.
    """
    oczekiwane = {
        "doradca.instrukcja_systemowa",
        "narzedzia.policz_podatek",
        "narzedzia.policz_podatek/sygnatura",
        "podatki.policz_fakture_z_bazy",
    }
    assert PRZESZLE == oczekiwane, (
        f"pomiar objal {len(PRZESZLE)} sciezek zamiast {len(oczekiwane)}: "
        f"brakuje {sorted(oczekiwane - PRZESZLE)}")
    assert len(PRZESZLE) == 4


# --- (c) KONTROLA DWUSTRONNA — przy RYCZALCIE sciezka dziala -------------

def test_przy_ryczalcie_silnik_ryczaltu_NADAL_liczy(baza_ryczalt):
    """Znika bezwarunkowosc, nie zdolnosc.

    Gdyby naprawa polegala na wykresleniu ryczaltu z aplikacji, ten test
    bylby czerwony — i o to chodzi. Ryczalt ma dzialac dla kogos, kto jest
    na ryczalcie.
    """
    forma, w = podatki.policz_fakture_z_bazy(
        baza_ryczalt, kwota_netto=NETTO, stawka_vat=STAWKA_VAT, dzien=DZIEN)
    assert forma.forma == magazyn.FORMA_RYCZALT
    assert isinstance(w, podatki.Wyliczenie), type(w).__name__
    assert w.podstawa_ryczaltu > 0
    # Ta sama liczba, co z silnika wolanego wprost — zbieracz nie liczy sam.
    wprost = podatki.policz_ryczalt(
        NETTO, Decimal("0.085"), STAWKA_VAT,
        magazyn.przychod_narastajaco(baza_ryczalt, ROK), False)
    assert w.pit == wprost.pit


def test_przy_ryczalcie_narzedzie_doradcy_zwraca_pojecia_ryczaltu(baza_ryczalt):
    n = narzedzia.zbuduj(baza_ryczalt)["policz_podatek"]
    wynik = n(kwota_netto=str(NETTO))
    assert wynik["nazwa_podatku"] == "Ryczałt"
    assert "podstawa_ryczaltu" in wynik


def test_przy_ryczalcie_instrukcja_doradcy_mowi_o_ryczalcie(baza_ryczalt):
    tekst = doradca.instrukcja_systemowa(baza_ryczalt, dzis=DZIEN)
    assert "ryczałtem" in tekst


# --- forma nierozstrzygnieta: ODMOWA, nie zgadywanie ---------------------

def test_bez_formy_nikt_nie_zgaduje(tmp_path):
    """Brak formy na rok = blad wywolania z poleceniem, nie liczba ryczaltowa.

    ZNALEZISKO 2026-08-28: swieza baza NIE jest „bez formy". `magazyn.
    _zaczep_formy` wpisuje do pustej tabeli `2026 / SKALA` (stala
    `ROK_ZACZEPU_FORMY`) — swiadomie i z uzasadnieniem w kodzie. Stan „brak
    formy" wytwarza sie wiec pytaniem o rok BEZ WPISU, nie pusta baza.
    Zapisanie tego tutaj jest czescia strazika: kto tego nie wie, napisze
    test, ktory mierzy co innego, niz mysli.
    """
    rok_bez_wpisu = magazyn.ROK_ZACZEPU_FORMY + 4
    p = magazyn.zmigruj_i_polacz()
    assert magazyn.forma_na_rok(p, rok_bez_wpisu).forma == \
        magazyn.FORMA_NIEROZSTRZYGNIETA
    with pytest.raises(magazyn.BladMagazynu) as blad:
        podatki.policz_fakture_z_bazy(
            p, kwota_netto=NETTO, stawka_vat=STAWKA_VAT,
            dzien=date(rok_bez_wpisu, 10, 5))
    assert "Ustawieniach" in str(blad.value)
    tekst = doradca.instrukcja_systemowa(p, dzis=date(rok_bez_wpisu, 10, 5))
    assert "NIEROZSTRZYGNIĘTEJ" in tekst
