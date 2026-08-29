"""Strazniki kosztow w porownaniu form opodatkowania (Zadanie 27).

Do 2026-08-25 `formy.porownaj_formy` liczyla BEZ kosztow i uczciwie to
zastrzegala. Zastrzezenie nie jest jednak neutralne: skala i liniowy pozwalaja
odliczyc koszty, ryczalt NIE — wiec porownanie bez kosztow pokazuje ryczalt
w lepszym swietle, niz zasluguje, i to tym bardziej, im wiecej kosztow masz.

Po Zadaniu 23 koszty leza w bazie (`koszty_jdg`), wiec zastrzezenie da sie
ZDJAC, a nie tylko powtarzac.

DLACZEGO KWOTA NETTO. Dla VAT-owca kosztem uzyskania przychodu jest kwota
NETTO — VAT naliczony wraca osobno przez rozliczenie VAT. Uzycie brutto
zawyzylo by koszt o VAT, ktory nie jest kosztem.
"""

from decimal import Decimal

from silnik.rdzen import formy, stawki

PRZYCHOD = Decimal("134400")


def _formy(koszty="0", przychod=PRZYCHOD, miesiecy=12):
    return {f.nazwa: f for f in formy.porownaj_formy(
        Decimal(przychod), miesiecy, koszty=Decimal(koszty))}


# --- regresja -------------------------------------------------------------

def test_zero_kosztow_daje_wynik_jak_przed_zmiana():
    """Domyslne wywolanie ma liczyc dokladnie to, co liczylo — inaczej
    zmiana cicho przesunelaby wszystkie dotychczasowe wyniki."""
    bez_parametru = {f.nazwa: f for f in formy.porownaj_formy(PRZYCHOD)}
    z_zerem = _formy("0")
    for nazwa, wynik in bez_parametru.items():
        assert wynik.razem == z_zerem[nazwa].razem
        assert wynik.do_dyspozycji == z_zerem[nazwa].do_dyspozycji


# --- granica: kto odlicza, a kto nie --------------------------------------

def test_koszty_NIE_ruszaja_ryczaltu():
    """Podstawa ryczaltu to PRZYCHOD. Odliczenie kosztow bylo by bledem
    merytorycznym, nie ulepszeniem."""
    bez, z_kosztami = _formy("0"), _formy("30000")
    for nazwa in ("ryczalt 8,5%", "ryczalt 15%"):
        assert z_kosztami[nazwa].pit == bez[nazwa].pit
        assert z_kosztami[nazwa].zdrowotna == bez[nazwa].zdrowotna
        assert z_kosztami[nazwa].razem == bez[nazwa].razem


def test_koszty_obnizaja_podatek_skali_i_liniowego():
    bez, z_kosztami = _formy("0"), _formy("30000")
    for nazwa in ("skala", "liniowy"):
        assert z_kosztami[nazwa].pit < bez[nazwa].pit, nazwa


def test_koszty_obnizaja_takze_skladke_zdrowotna_poza_ryczaltem():
    """Na skali i liniowym zdrowotna liczy sie OD DOCHODU, wiec koszt zbija
    takze ja. Pominiecie tego zanizyloby przewage skali nad ryczaltem."""
    bez, z_kosztami = _formy("0"), _formy("30000")
    for nazwa in ("skala", "liniowy"):
        assert z_kosztami[nazwa].zdrowotna < bez[nazwa].zdrowotna, nazwa


def test_zdrowotna_nie_schodzi_ponizej_minimum(  ):
    """Koszty wieksze od przychodu nie zwalniaja ze skladki minimalnej."""
    wyniki = _formy("500000")
    minimum = stawki.do_zlotych(stawki.ZDROWOTNA_MIN_MIESIECZNA * 12)
    for nazwa in ("skala", "liniowy"):
        assert wyniki[nazwa].zdrowotna == minimum, nazwa
        assert wyniki[nazwa].pit == Decimal("0"), nazwa


# --- co zostaje w kieszeni ------------------------------------------------

def test_do_dyspozycji_odejmuje_koszty_we_WSZYSTKICH_formach():
    """Koszt wyplynal z konta niezaleznie od formy opodatkowania. Liczba
    „do dyspozycji" bez niego obiecuje pieniadze, ktorych nie ma."""
    bez, z_kosztami = _formy("0"), _formy("30000")
    for nazwa in bez:
        assert (z_kosztami[nazwa].do_dyspozycji
                == bez[nazwa].do_dyspozycji - Decimal("30000")
                + (bez[nazwa].razem - z_kosztami[nazwa].razem)), nazwa


def test_koszty_przesuwaja_ranking_na_niekorzysc_ryczaltu():
    """Sedno tego zadania. Przy duzych kosztach ryczalt traci wzgledem skali
    i liniowego — i porownanie bez kosztow tego NIE POKAZYWALO."""
    bez = _formy("0")
    duze = _formy("60000")
    luka_bez = bez["ryczalt 8,5%"].razem - bez["liniowy"].razem
    luka_duze = duze["ryczalt 8,5%"].razem - duze["liniowy"].razem
    assert luka_duze > luka_bez


# --- zastrzezenia ida za rzeczywistoscia ----------------------------------

def test_bez_kosztow_zastrzezenie_zostaje():
    tekst = " ".join(_formy("0")["skala"].zastrzezenia)
    assert "koszt" in tekst.lower()


def test_z_kosztami_zastrzezenie_o_ich_braku_znika():
    """Powtarzanie „zero kosztow", gdy koszty sa uwzglednione, jest falszem
    — i to falszem, ktory podwaza zaufanie do reszty zastrzezen."""
    tekst = " ".join(_formy("30000")["skala"].zastrzezenia)
    assert "Zero kosztów" not in tekst
    assert "30000" in tekst.replace(" ", "") or "30 000" in tekst


def test_z_kosztami_pada_wprost_ze_ryczalt_ich_nie_odlicza():
    tekst = " ".join(_formy("30000")["ryczalt 8,5%"].zastrzezenia).lower()
    assert "nie odlicza kosztów" in tekst


# --- doradca liczy z realnymi kosztami ------------------------------------

def test_doradca_bierze_koszty_z_ewidencji(tmp_path):
    """Do 2026-08-25 narzedzie doradcy zawsze liczylo z zerem, wiec na pytanie
    „czy rycza t sie oplaca" odpowiadalo korzystniej dla ryczaltu, niz wynika
    z danych, ktore samo ma w bazie."""
    from datetime import date

    from silnik.rdzen import magazyn, narzedzia

    p = magazyn.zmigruj_i_polacz(tmp_path / "formy.db")
    rok = date.today().year
    magazyn.zapisz_koszt(p, data=date(rok, 3, 10), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    wynik = narzedzia.zbuduj(p)["porownaj_formy"](przychod_roczny="134400")
    assert wynik["koszty_uzyskania_netto"] == "4000.00"
    assert wynik["rok_kosztow"] == rok


def test_doradca_bierze_NETTO_a_nie_brutto(tmp_path):
    """Dla VAT-owca kosztem jest netto; VAT naliczony wraca osobno."""
    from datetime import date

    from silnik.rdzen import magazyn

    p = magazyn.zmigruj_i_polacz(tmp_path / "netto.db")
    rok = date.today().year
    magazyn.zapisz_koszt(p, data=date(rok, 3, 10), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    assert magazyn.koszty_netto_w_roku(p, rok) == Decimal("4000.00")


def test_koszty_z_innego_roku_nie_wchodza(tmp_path):
    from datetime import date

    from silnik.rdzen import magazyn

    p = magazyn.zmigruj_i_polacz(tmp_path / "rok.db")
    magazyn.zapisz_koszt(p, data=date(2025, 3, 10), opis="stare",
                         kwota_netto=Decimal("9999.00"),
                         kwota_vat=Decimal("0.00"))
    assert magazyn.koszty_netto_w_roku(p, 2026) == Decimal("0.00")
    assert magazyn.koszty_netto_w_roku(p, 2025) == Decimal("9999.00")
