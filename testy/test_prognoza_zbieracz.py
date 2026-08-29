"""Cienki zbieracz prognozy plynnosci — czyta baze, wola silnik (Z63).

Rozdzial jest ten sam co przy `podatki.rezerwa_z_bazy` (Z55): rachunek jest
CZYSTY i sprawdzalny na argumentach (Z62), zbieranie jest OSOBNO i cienkie.
Bez tego kazdy konsument — ekran, punkt koncowy API, straznik w tle —
powtarzalby ten sam zestaw odczytow, a kazde powtorzenie to okazja, zeby
jeden z nich podal silnikowi co innego.

Zmierzone uzasadnienie tej dyscypliny (audyt 2026-08-26): ekran pokazywal
-6 098,11 zl, a doradca +8 007,89 zl o TEJ SAMEJ rzeczy w TEJ SAMEJ chwili.
"""

from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import (budzet, magazyn, podatki, prognoza_plynnosci as prognoza,
                   stawki)


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.polacz(tmp_path / "test.db")
    yield polaczenie
    polaczenie.close()


def _faktura(p, *, data: date, netto: str, numer: str):
    magazyn.zapisz_fakture(
        p, data=data, numer_faktury=numer, kwota_netto=Decimal(netto),
        stawka_vat=stawki.STAWKA_VAT_DOMYSLNA,
        kwota_vat=stawki.do_groszy(Decimal(netto) * stawki.STAWKA_VAT_DOMYSLNA),
        pkwiu="46.19.10.0", stawka_ryczaltu=Decimal("0.085"),
        zaplacony_zus=Decimal("1600.32"),
        zysk_netto=Decimal(netto) - Decimal("2000.00"),
        stawki_wersja="2026-08")


# --- kotwica obowiazujaca ------------------------------------------------

def test_ostatnia_kotwica_bierze_NAJNOWSZY_odczyt(p):
    """JEDEN nosnik odpowiedzi „ktora kotwica obowiazuje". Ekran, API
    i straznik w tle musza dostac te sama — inaczej prognoza na pulpicie
    i prognoza w powiadomieniu startuja z roznych punktow."""
    for dzien, kwota in ((1, "5000.00"), (27, "1840.55"), (15, "3200.10")):
        magazyn.zapisz_stan_konta(p, data=date(2026, 8, dzien),
                                  kwota=Decimal(kwota))
    kotwica = prognoza.ostatnia_kotwica(p)
    assert kotwica.data == date(2026, 8, 27)
    assert kotwica.kwota == Decimal("1840.55")


def test_brak_kotwicy_daje_None_a_nie_zero(p):
    """Zero to najlepszy mozliwy stan konta pokazany wtedy, gdy nie wiadomo
    nic. `None` idzie do silnika i wraca jako „nie wiem" (R11)."""
    assert prognoza.ostatnia_kotwica(p) is None


# --- ustawienia prognozy (E4, R17) ---------------------------------------

def test_wolumen_bez_ustawien_bierze_wartosci_STARTOWE(p):
    """R17: 120 h ostroznie, 160 h realnie, 70 zl za godzine. Wartosci
    startowe, nie zaszyte — Darek zmienia je w aplikacji."""
    w = prognoza.wolumen_z_bazy(p)
    assert w.ostrozny == Decimal("120")
    assert w.realny == Decimal("160")
    assert w.stawka == Decimal("70")


def test_zapisany_wolumen_WRACA_co_do_grosza(p):
    magazyn.zapisz_ustawienia_prognozy(
        p, ostrozny=Decimal("100.5"), realny=Decimal("175"),
        stawka=Decimal("82.50"))
    w = prognoza.wolumen_z_bazy(p)
    assert (w.ostrozny, w.realny, w.stawka) \
        == (Decimal("100.5"), Decimal("175"), Decimal("82.50"))


def test_WYCZYSZCZONY_wolumen_ostrozny_ODMAWIA_obu_linii(p):
    """R17 doslownie. WYCZYSZCZENIE to nie to samo co NIEUSTAWIENIE:
    brak wpisu znaczy „jeszcze nie decydowalem" i bierze wartosc startowa,
    pusty wpis znaczy „nie uznaje zadnego wolumenu za pewny".

    Rysowanie samej realnej daloby zielony obraz z wylaczonym mechanizmem
    ostrzegania — dlatego odmowa dotyczy OBU linii."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 9, 1), kwota=Decimal("1000"))
    magazyn.zapisz_ustawienia_prognozy(p, ostrozny=None, realny=Decimal("160"),
                                       stawka=Decimal("70"))
    assert prognoza.wolumen_z_bazy(p).ostrozny is None
    wynik = prognoza.prognozuj(p, dzis=date(2026, 9, 1))
    assert wynik.stan == prognoza.STAN_NIE_WIEM
    assert wynik.dni is None


def test_wolumen_uszkodzony_w_bazie_jest_BLEDEM_nie_cichym_brakiem(p):
    """„Mam zla wartosc" i „nie mam wartosci" to dwa rozne stany, a drugi
    z nich milczy zamiast krzyczec. Ta sama regula co przy dacie
    rozpoczecia dzialalnosci (Z54)."""
    magazyn.ustaw_ustawienie(p, magazyn.KLUCZ_WOLUMEN_OSTROZNY, "sto dwadziescia")
    with pytest.raises(magazyn.BladMagazynu) as blad:
        prognoza.wolumen_z_bazy(p)
    assert "wolumen" in str(blad.value).lower()


# --- zbieracz nie liczy NICZEGO sam --------------------------------------

def test_zbieracz_daje_DOKLADNIE_to_co_silnik_na_tych_samych_danych(p):
    """Straznik jednego nosnika, wzorowany na `test_narzedzia.py:224`
    (kwota doradcy kontra kwota silnika). Gdyby zbieracz cokolwiek liczyl
    po drodze — inny wolumen, inna forma, inny horyzont — te dwie drogi
    rozjechalyby sie po cichu i przy zielonej suicie."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 9, 1), kwota=Decimal("10000"))
    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_SKALA)
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ=budzet.TYP_WYDATKI,
                        kategoria="Zakupy", kwota_planowana=Decimal("500.00"),
                        powtarzalna=1, dzien=10)

    ze_zbieracza = prognoza.prognozuj(p, dzis=date(2026, 9, 1))
    z_silnika = prognoza.zbuduj(
        plan=magazyn.wczytaj_plan(p),
        kotwica=prognoza.ostatnia_kotwica(p),
        wolumen=prognoza.wolumen_z_bazy(p),
        forma=magazyn.forma_na_rok(p, 2026),
        zaleglosci=podatki.do_zaplaty(
            podatki.rezerwa_z_bazy(p, dzis=date(2026, 9, 1)),
            date(2026, 9, 1), magazyn.wczytaj_wpisy(p)),
        przychod_narastajaco=magazyn.przychod_narastajaco(p, 2026),
        dzis=date(2026, 9, 1),
        dochod_narastajaco=podatki.stan_roku_skali(
            magazyn.wczytaj_faktury(p), 2026).dochod_narastajaco,
        zaliczki_naliczone=podatki.stan_roku_skali(
            magazyn.wczytaj_faktury(p), 2026).zaliczki_przed_zaokragleniem,
        zobowiazania=magazyn.wczytaj_zobowiazania(p))

    assert len(ze_zbieracza.dni) == len(z_silnika.dni) > 150
    assert [d.saldo_ostrozne for d in ze_zbieracza.dni] \
        == [d.saldo_ostrozne for d in z_silnika.dni]
    assert [d.saldo_realne for d in ze_zbieracza.dni] \
        == [d.saldo_realne for d in z_silnika.dni]


def test_zbieracz_PODAJE_silnikowi_forme_z_bazy(p):
    """Kontrola dwustronna: gdyby zbieracz zaszyl forme, zmiana w Ustawieniach
    nie ruszalaby prognozy — i nikt by tego nie zauwazyl, bo liczby dalej
    by sie pojawialy."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 9, 1), kwota=Decimal("10000"))
    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu=Decimal("0.085"))
    wynik = prognoza.prognozuj(p, dzis=date(2026, 9, 1))
    nazwy = {z.nazwa for d in wynik.dni for z in d.zdarzenia}
    assert "Ryczałt" in nazwy and "PIT" not in nazwy

    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_SKALA)
    wynik = prognoza.prognozuj(p, dzis=date(2026, 9, 1))
    nazwy = {z.nazwa for d in wynik.dni for z in d.zdarzenia}
    assert "PIT" in nazwy and "Ryczałt" not in nazwy


def test_zbieracz_PODAJE_silnikowi_zaleglosci_z_rezerwy(p):
    """Zaleglosc pochodzi z realnych faktur. Zbieracz, ktory jej nie poda,
    pokaze prognoze zawyzona o wszystko, co juz wisi u urzedu."""
    magazyn.zapisz_stan_konta(p, data=date(2026, 9, 1), kwota=Decimal("10000"))
    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu=Decimal("0.085"))
    magazyn.zapisz_dzialalnosc_od(p, date(2026, 8, 1))
    _faktura(p, data=date(2026, 8, 10), netto="12000.00", numer="F/2026/08/1")

    z_zalegloscia = prognoza.prognozuj(p, dzis=date(2026, 9, 1))
    # Ta sama droga, ale BEZ zaleglosci — porownanie zamiast furtki
    # testowej w kodzie produkcyjnym.
    bez = prognoza.zbuduj(
        plan=magazyn.wczytaj_plan(p), kotwica=prognoza.ostatnia_kotwica(p),
        wolumen=prognoza.wolumen_z_bazy(p),
        forma=magazyn.forma_na_rok(p, 2026), zaleglosci=[],
        przychod_narastajaco=magazyn.przychod_narastajaco(p, 2026),
        dzis=date(2026, 9, 1))
    zaleglosci = [z for d in z_zalegloscia.dni for z in d.zdarzenia
                  if z.rodzaj == prognoza.RODZAJ_ZALEGLOSC]
    assert zaleglosci, "kontrola licznosci: zadnej zaleglosci mimo faktury"
    assert z_zalegloscia.dni[-1].saldo_ostrozne < bez.dni[-1].saldo_ostrozne


# --- stan roku dla skali: JEDEN nosnik przebiegu narastajaco -------------

def test_stan_roku_skali_zgadza_sie_z_PODATKIEM_dochodowym(p):
    """Straznik jednego nosnika. `podatki._podatek_dochodowy` prowadzil ten
    sam przebieg narastajaco w swoim srodku; po wydzieleniu obie drogi musza
    dawac te sama liczbe, inaczej wydzielenie bylo kopia."""
    _faktura(p, data=date(2026, 3, 10), netto="12000.00", numer="F/1")
    _faktura(p, data=date(2026, 4, 10), netto="14000.00", numer="F/2")
    _faktura(p, data=date(2026, 5, 10), netto="11000.00", numer="F/3")
    faktury = magazyn.wczytaj_faktury(p)

    stan = podatki.stan_roku_skali(faktury, 2026)
    assert stan.faktur == 3, f"pomiar widzial {stan.faktur} faktur, nie trzy"
    assert stawki.do_zlotych(max(Decimal("0"), stan.zaliczki_przed_zaokragleniem)) \
        == podatki._podatek_dochodowy(faktury, magazyn.FORMA_SKALA)

    # Liczby ZMIERZONE (2026-08-27), nie przepisane z drugiej strony
    # rownania. Asercja wyzej porownuje `stan_roku_skali` z funkcja, ktora
    # od Z63 JA WOLA — czyli sama ze soba; bez tych dwoch stalych mutacja
    # „kumuluj zaliczki PO zaokragleniu" przechodzila caly przebieg
    # (M280 przezyla 721 testow).
    assert stan.dochod_narastajaco == Decimal("31219.72")
    assert stan.zaliczki_przed_zaokragleniem == Decimal("146.37")


def test_stan_roku_skali_dla_INNEGO_roku_jest_pusty(p):
    """Kontrola dwustronna: stan, ktory zwraca to samo dla kazdego roku,
    zamienilby przelom roku w bezruch."""
    _faktura(p, data=date(2026, 3, 10), netto="12000.00", numer="F/1")
    stan = podatki.stan_roku_skali(magazyn.wczytaj_faktury(p), 2027)
    assert stan.faktur == 0
    assert stan.dochod_narastajaco == Decimal("0.00")
    assert stan.zaliczki_przed_zaokragleniem == Decimal("0.00")


def test_zaliczka_prognozy_kumuluje_sie_PRZED_zaokragleniem(p):
    """Ta sama regula co w silniku (`podatki.stan_roku_skali`): narastajaco
    niesie zaliczke PRZED zaokragleniem, a placi sie kwote PO zaokragleniu.

    Kumulowanie zaokraglonych zaliczek byloby DRUGIM NOSNIKIEM tej reguly,
    a rozjazd rosnie z kazdym miesiacem i nigdy nie przekroczy progu, ktory
    ktos by zauwazyl. Zmierzone 2026-08-27 przy 400 h miesiecznie:

        kumulacja PRZED zaokragleniem: 2658.00, 3129.00, 3129.00   <- silnik
        kumulacja PO  zaokragleniu   : 2658.00, 3128.00, 3129.00

    Wolumen 400 h, nie startowe 120 h — przy 120 h kwota zmniejszajaca
    3 600 zl zjada cala zaliczke i zdarzen PIT nie ma wcale, wiec przypadek
    nie rozroznialby niczego. Zaliczka za wrzesien jest zerowa z tego samego
    powodu i dlatego zdarzen jest trzy, nie piec.
    """
    magazyn.zapisz_stan_konta(p, data=date(2026, 9, 1), kwota=Decimal("10000"))
    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_SKALA)
    magazyn.zapisz_ustawienia_prognozy(p, ostrozny=Decimal("400"),
                                       realny=Decimal("400"),
                                       stawka=Decimal("70"))

    wynik = prognoza.prognozuj(p, dzis=date(2026, 9, 1))
    pity = [str(-z.kwota_ostrozna) for d in wynik.dni for z in d.zdarzenia
            if z.nazwa == "PIT"]
    assert len(pity) == 3, f"zaliczek PIT na osi jest {len(pity)}, nie trzy"
    assert pity == ["2658.00", "3129.00", "3129.00"], \
        f"zaliczki nie zgadzaja sie z silnikiem: {pity}"


def test_stan_roku_ZMIENIA_prognoze_a_nie_tylko_do_niej_wchodzi():
    """Straznik dolozony po przebiegu mutacyjnym. Mutacja M279 — podanie
    silnikowi zer zamiast stanu roku — PRZEZYLA komplet 721 testow, bo
    zaden przypadek nie mial faktur sprzed prognozy: `stan_roku_skali`
    zwracalo zera i obie drogi dawaly to samo.

    Zmierzone 2026-08-27 na trzech fakturach z marca, kwietnia i maja
    (dochod narastajaco 31 219,72 zl, zaliczki 146,37 zl):

        ze STANEM roku : cztery zaliczki po 777,00 zl
        z ZERAMI       : jedna zaliczka 0,00 zl

    Zanizenie idzie w kierunku, ktory POPRAWIA obraz — czyli w najgorszym
    mozliwym. Kwota zmniejszajaca 3 600 zl zostaje wtedy wzieta drugi raz.
    """
    import tempfile
    from pathlib import Path as _Path

    katalog = _Path(tempfile.mkdtemp())
    polaczenie = magazyn.polacz(katalog / "stan.db")
    try:
        for dzien, netto, numer in ((date(2026, 3, 10), "12000.00", "F/1"),
                                    (date(2026, 4, 10), "14000.00", "F/2"),
                                    (date(2026, 5, 10), "11000.00", "F/3")):
            _faktura(polaczenie, data=dzien, netto=netto, numer=numer)
        magazyn.zapisz_stan_konta(polaczenie, data=date(2026, 9, 1),
                                  kwota=Decimal("10000"))
        magazyn.zapisz_forme(polaczenie, rok=2026, forma=magazyn.FORMA_SKALA)

        wynik = prognoza.prognozuj(polaczenie, dzis=date(2026, 9, 1))
        pity = [str(-z.kwota_ostrozna) for d in wynik.dni for z in d.zdarzenia
                if z.nazwa == "PIT"]
        # Pierwsza pozycja to ZALEGLOSC — 146,00 zl zaliczki juz naliczonej
        # z trzech faktur (`podatki.do_zaplaty`); cztery nastepne to zaliczki
        # PROGNOZOWANE. Obie drogi widac naraz i to jest wlasnie sedno:
        # zaleglosc niesie to, co juz wisi, a prognoza to, co dopiero
        # narosnie — z tego samego stanu roku.
        assert pity == ["146.00", "777.00", "777.00", "777.00", "777.00"], \
            f"prognoza nie wziela stanu roku: {pity}"
    finally:
        polaczenie.close()
