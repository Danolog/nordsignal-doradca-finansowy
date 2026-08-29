"""Strazniki czystego rdzenia budzetu - arytmetyka bez bazy i bez interfejsu.

Kontrole licznosci sa tu osobnymi testami, nie doklejka do asercji: sprawdzenie,
do ktorego nic nie dociera, melduje sukces. Suma pustego zbioru rowna sie zeru,
wiec test sumy przechodzi na pustych danych i nie mierzy niczego.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import budzet


def _wpisy(*krotki) -> pd.DataFrame:
    """Buduje ramke wpisow z krotek (data, typ, kategoria, kwota)."""
    return pd.DataFrame([
        {"data": d, "typ": t, "kategoria": k, "kwota": Decimal(kw)}
        for d, t, k, kw in krotki
    ])


def _plan(*krotki) -> pd.DataFrame:
    """Buduje ramke planu z krotek (rok, miesiac, typ, kategoria, kwota)."""
    return pd.DataFrame([
        {"rok": r, "miesiac": m, "typ": t, "kategoria": k,
         "kwota_planowana": Decimal(kw)}
        for r, m, t, k, kw in krotki
    ])


# --- kontrole licznosci ---------------------------------------------------

def test_typy_to_dokladnie_trzy_wartosci():
    """Kontrola licznosci: gdyby krotka byla pusta, walidacja typu nie miala
    by czego odrzucac i przepuszczalaby wszystko przy zielonej suicie."""
    assert len(budzet.TYPY) == 3
    assert budzet.TYPY == ("Przychody", "Wydatki", "Oszczędności")


def test_kategorie_startowe_licznosc_zgodna_z_arkuszem():
    """Odczyt arkusza 2026-08-25: 4 przychody, 15 wydatkow, 4 oszczednosci.

    Liczby pinuje sie do POMIARU arkusza, nie do zawartosci slownika — inaczej
    kazde nasze dolozenie kategorii „naprawialoby" straznika przez podbicie
    liczby i przeslanka „slownik odpowiada arkuszowi" zniknelaby po cichu.
    """
    assert len(budzet.KATEGORIE_STARTOWE["Przychody"]) == 4
    assert len(budzet.WYDATKI_Z_ARKUSZA) == 15
    assert len(budzet.KATEGORIE_STARTOWE["Oszczędności"]) == 4
    razem_z_arkusza = (len(budzet.KATEGORIE_STARTOWE["Przychody"])
                       + len(budzet.WYDATKI_Z_ARKUSZA)
                       + len(budzet.KATEGORIE_STARTOWE["Oszczędności"]))
    assert razem_z_arkusza == 23


def test_kategorie_spoza_arkusza_sa_wymienione_z_nazwy():
    """Dolozone przez nas kategorie maja byc policzalne i nazwane. Wsuniecie
    czegokolwiek do krotki arkuszowej zaczerwieni straznika wyzej."""
    assert budzet.KATEGORIE_SPOZA_ARKUSZA == (budzet.KATEGORIA_PODATKI,)
    assert set(budzet.KATEGORIE_STARTOWE["Wydatki"]) == (
        set(budzet.WYDATKI_Z_ARKUSZA) | set(budzet.KATEGORIE_SPOZA_ARKUSZA))


def test_kategorie_startowe_maja_klucze_dokladnie_z_typow():
    assert set(budzet.KATEGORIE_STARTOWE) == set(budzet.TYPY)


def test_inne_wystepuje_w_dwoch_roznych_typach():
    """Klucz kategorii to para (typ, nazwa), nigdy sama nazwa.

    W arkuszu `Inne` jest jednoczesnie kategoria przychodu i wydatku. Kod
    trzymajacy kategorie po samej nazwie sklei je w jedna pozycje.
    """
    assert "Inne" in budzet.KATEGORIE_STARTOWE["Przychody"]
    assert "Inne" in budzet.KATEGORIE_STARTOWE["Wydatki"]
    assert "Inne" not in budzet.KATEGORIE_STARTOWE["Oszczędności"]


# --- znak wg typu ---------------------------------------------------------

@pytest.mark.parametrize("typ, oczekiwany", [
    ("Przychody", 1),
    ("Wydatki", -1),
    ("Oszczędności", -1),
])
def test_znak_wynika_z_typu(typ, oczekiwany):
    """Oszczednosci pomniejszaja srodki do alokacji tak samo jak wydatki -
    pieniadz odlozony przestaje byc do dyspozycji. To jest sedno budzetu zerowego."""
    assert budzet.znak(typ) == oczekiwany


def test_znak_odrzuca_typ_spoza_slownika():
    with pytest.raises(ValueError) as blad:
        budzet.znak("Inwestycje")
    assert "Inwestycje" in str(blad.value)


# --- saldo narastajace ----------------------------------------------------

def test_saldo_narastajaco_sumuje_ze_znakiem_wg_typu():
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "8130.78"),
        ("2025-10-02", "Wydatki", "Transport", "6.00"),
        ("2025-10-03", "Oszczędności", "Reszta Revolut", "2.02"),
        ("2025-10-04", "Wydatki", "Zakupy", "13.99"),
    )
    saldo = budzet.saldo_narastajaco(wpisy)
    assert saldo == [
        Decimal("8130.78"),
        Decimal("8124.78"),
        Decimal("8122.76"),
        Decimal("8108.77"),
    ]


def test_saldo_narastajaco_widzialo_kazdy_wpis():
    """Kontrola licznosci: lista krotsza niz ramka znaczy, ze czesc wpisow
    wypadla po cichu, a ostatnia wartosc i tak wygladalaby wiarygodnie."""
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "100.00"),
        ("2025-10-02", "Wydatki", "Zakupy", "10.00"),
        ("2025-10-03", "Wydatki", "Zakupy", "10.00"),
    )
    assert len(budzet.saldo_narastajaco(wpisy)) == len(wpisy) == 3


def test_saldo_narastajaco_na_pustej_ramce_daje_pusta_liste():
    assert budzet.saldo_narastajaco(_wpisy()) == []


# --- do alokacji ----------------------------------------------------------

def test_do_alokacji_odejmuje_takze_oszczednosci():
    """Budzet zerowy: do alokacji = przychody - wydatki - OSZCZEDNOSCI.

    Pominiecie oszczednosci daje liczbe zawyzona i zachecajaca do wydania
    pieniedzy, ktore sa juz przeznaczone na cel.
    """
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "8130.78"),
        ("2025-10-05", "Wydatki", "Zakupy", "1000.00"),
        ("2025-10-06", "Oszczędności", "Reszta Revolut", "130.78"),
    )
    assert budzet.do_alokacji(wpisy, 2025, 10) == Decimal("7000.00")


def test_do_alokacji_bierze_wylacznie_wybrany_miesiac():
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "8000.00"),
        ("2025-11-01", "Przychody", "Wynagrodzenie", "6500.00"),
        ("2025-11-05", "Wydatki", "Zakupy", "500.00"),
    )
    assert budzet.do_alokacji(wpisy, 2025, 10) == Decimal("8000.00")
    assert budzet.do_alokacji(wpisy, 2025, 11) == Decimal("6000.00")


def test_do_alokacji_na_miesiacu_bez_wpisow_daje_zero():
    wpisy = _wpisy(("2025-10-01", "Przychody", "Wynagrodzenie", "8000.00"))
    assert budzet.do_alokacji(wpisy, 2025, 12) == Decimal("0.00")


# --- plan kontra wykonanie ------------------------------------------------

def test_wykonanie_liczone_wobec_planu_tego_samego_miesiaca():
    """Plan sumowany rocznie zamiast miesiecznie zanizy procent trzykrotnie
    i pokaze mieszczenie sie w budzecie tam, gdzie go nie ma."""
    wpisy = _wpisy(
        ("2025-10-05", "Wydatki", "Zakupy", "1500.00"),
        ("2025-11-05", "Wydatki", "Zakupy", "1500.00"),
        ("2025-12-05", "Wydatki", "Zakupy", "1500.00"),
    )
    plan = _plan(
        (2025, 10, "Wydatki", "Zakupy", "1500.00"),
        (2025, 11, "Wydatki", "Zakupy", "1500.00"),
        (2025, 12, "Wydatki", "Zakupy", "2500.00"),
    )
    pozycje = {w.kategoria: w for w in budzet.wykonanie_planu(wpisy, plan, 2025, 10)}
    assert pozycje["Zakupy"].planowane == Decimal("1500.00")
    assert pozycje["Zakupy"].wykonane == Decimal("1500.00")
    assert pozycje["Zakupy"].procent == Decimal("100")
    assert pozycje["Zakupy"].pozostalo == Decimal("0.00")


def test_wykonanie_zglasza_przekroczenie_planu():
    wpisy = _wpisy(("2025-10-05", "Wydatki", "Transport", "2400.00"))
    plan = _plan((2025, 10, "Wydatki", "Transport", "2000.00"))
    pozycja = budzet.wykonanie_planu(wpisy, plan, 2025, 10)[0]
    assert pozycja.przekroczone is True
    assert pozycja.pozostalo == Decimal("-400.00")
    assert pozycja.procent == Decimal("120")


def test_wykonanie_pokazuje_kategorie_z_planem_ale_bez_wydatku():
    """Kategoria zaplanowana i nietkniete pieniadze to informacja, nie brak
    danych - musi byc widoczna na liscie, inaczej plan znika z ekranu."""
    plan = _plan((2025, 10, "Wydatki", "Czesne", "660.00"))
    pozycja = budzet.wykonanie_planu(_wpisy(), plan, 2025, 10)[0]
    assert pozycja.wykonane == Decimal("0.00")
    assert pozycja.procent == Decimal("0")
    assert pozycja.przekroczone is False


def test_wykonanie_pokazuje_wydatek_bez_planu_z_procentem_nieokreslonym():
    """Wydatek w kategorii bez planu nie ma sie do czego odniesc. Procent 0
    klamalby, ze zmiescil sie w budzecie; procent 100 - ze go wyczerpal."""
    wpisy = _wpisy(("2025-10-05", "Wydatki", "PUWIS", "523.30"))
    pozycja = budzet.wykonanie_planu(wpisy, _plan(), 2025, 10)[0]
    assert pozycja.planowane == Decimal("0.00")
    assert pozycja.wykonane == Decimal("523.30")
    assert pozycja.procent is None
    assert pozycja.przekroczone is True


def test_wykonanie_widzi_wszystkie_kategorie_obu_zrodel():
    """Kontrola licznosci: suma unikalnych par (typ, kategoria) z wpisow i planu."""
    wpisy = _wpisy(
        ("2025-10-05", "Wydatki", "Zakupy", "100.00"),
        ("2025-10-06", "Wydatki", "Transport", "50.00"),
        ("2025-10-07", "Przychody", "Wynagrodzenie", "8000.00"),
    )
    plan = _plan(
        (2025, 10, "Wydatki", "Zakupy", "1500.00"),
        (2025, 10, "Wydatki", "Czesne", "660.00"),
    )
    pozycje = budzet.wykonanie_planu(wpisy, plan, 2025, 10)
    assert len(pozycje) == 4
    assert {(p.typ, p.kategoria) for p in pozycje} == {
        ("Wydatki", "Zakupy"), ("Wydatki", "Transport"),
        ("Wydatki", "Czesne"), ("Przychody", "Wynagrodzenie"),
    }


# --- dane pod wykresy pulpitu (Zadanie 19) --------------------------------

def test_wydatki_wg_kategorii_nie_gubia_ani_zlotowki():
    """Wykres pierscieniowy klamie cicho: brakujaca kategoria po prostu nie ma
    wycinka i nikt nie zauwazy, ze suma udzialow nie zgadza sie z suma wydatkow.

    Dlatego straznik porownuje SUME UDZIALOW z suma wpisow, a nie sprawdza
    obecnosci konkretnej kategorii.
    """
    wpisy = _wpisy(
        ("2025-10-01", "Wydatki", "Zakupy", "100.00"),
        ("2025-10-02", "Wydatki", "Transport", "50.50"),
        ("2025-10-03", "Wydatki", "Zakupy", "25.25"),
        ("2025-10-04", "Przychody", "Wynagrodzenie", "8000.00"),
        ("2025-10-05", "Oszczędności", "Inwestycje", "500.00"),
    )
    udzialy = budzet.wydatki_wg_kategorii(wpisy, 2025, 10)
    assert sum((kwota for _, kwota in udzialy), Decimal("0.00")) \
        == Decimal("175.75")
    assert dict(udzialy) == {"Zakupy": Decimal("125.25"),
                             "Transport": Decimal("50.50")}


def test_wydatki_wg_kategorii_pomijaja_inne_typy():
    """Przychod i oszczednosc na wykresie WYDATKOW to nie ozdoba, tylko klamstwo."""
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "8000.00"),
        ("2025-10-02", "Oszczędności", "Inwestycje", "500.00"),
    )
    assert budzet.wydatki_wg_kategorii(wpisy, 2025, 10) == []


def test_wydatki_wg_kategorii_od_najwiekszej():
    wpisy = _wpisy(
        ("2025-10-01", "Wydatki", "Gaz", "10.00"),
        ("2025-10-02", "Wydatki", "Zakupy", "300.00"),
        ("2025-10-03", "Wydatki", "Transport", "100.00"),
    )
    assert [k for k, _ in budzet.wydatki_wg_kategorii(wpisy, 2025, 10)] \
        == ["Zakupy", "Transport", "Gaz"]


def test_ostatnie_miesiace_przechodza_przez_granice_roku():
    """Grudzien minus trzy to wrzesien, ale styczen minus trzy to pazdziernik
    ROKU POPRZEDNIEGO. Odejmowanie samego numeru miesiaca daje tu zero i minus
    jeden - miesiace, ktorych nie ma.
    """
    assert budzet.ostatnie_miesiace(2026, 2, 4) == [
        (2025, 11), (2025, 12), (2026, 1), (2026, 2)]
    assert budzet.ostatnie_miesiace(2025, 12, 3) == [
        (2025, 10), (2025, 11), (2025, 12)]


def test_ostatnie_miesiace_zwraca_dokladnie_tyle_ile_poproszono():
    """Kontrola licznosci: krotsza lista da wykres z brakujacymi slupkami,
    ktory wyglada tak samo jak wykres miesiecy bez danych."""
    for ile in (1, 6, 12, 18):
        assert len(budzet.ostatnie_miesiace(2026, 3, ile)) == ile


def test_sumy_miesieczne_licza_kazdy_typ_osobno():
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "8000.00"),
        ("2025-10-02", "Wydatki", "Zakupy", "1000.00"),
        ("2025-10-03", "Oszczędności", "Inwestycje", "500.00"),
        ("2025-11-01", "Wydatki", "Zakupy", "200.00"),
    )
    sumy = budzet.sumy_miesieczne(wpisy, [(2025, 10), (2025, 11)])
    assert sumy[(2025, 10)] == {
        "Przychody": Decimal("8000.00"),
        "Wydatki": Decimal("1000.00"),
        "Oszczędności": Decimal("500.00"),
    }
    assert sumy[(2025, 11)]["Wydatki"] == Decimal("200.00")
    assert sumy[(2025, 11)]["Przychody"] == Decimal("0.00")


def test_sumy_miesieczne_maja_wpis_dla_kazdego_zadanego_miesiaca():
    """Miesiac bez danych ma dac zera, nie zniknac z wykresu.

    Kontrola licznosci: brak klucza znaczy brak slupka, a brak slupka wyglada
    identycznie jak slupek zerowy - tylko przesuwa oś czasu.
    """
    miesiace = budzet.ostatnie_miesiace(2026, 3, 6)
    sumy = budzet.sumy_miesieczne(_wpisy(), miesiace)
    assert set(sumy) == set(miesiace)
    assert len(sumy) == 6
    for wartosci in sumy.values():
        assert set(wartosci) == set(budzet.TYPY)
        assert all(v == Decimal("0.00") for v in wartosci.values())


# --- cele oszczednosciowe (Zadanie 20) ------------------------------------

def test_postep_celu_liczony_z_REALNYCH_wpisow_nie_z_recznej_liczby():
    """Sedno tego straznika: postep ma wynikac z tego, co faktycznie odlozono.

    Pasek postepu napedzany reczna liczba pokazuje to, co uzytkownik wpisal,
    a nie to, co ma na koncie - czyli dokladnie odwrotnie, niz obiecuje.
    """
    wpisy = _wpisy(
        ("2025-10-01", "Oszczędności", "Poduszka finansowa", "1000.00"),
        ("2025-11-01", "Oszczędności", "Poduszka finansowa", "1500.00"),
        ("2025-11-02", "Oszczędności", "Inwestycje", "9999.00"),
        ("2025-11-03", "Wydatki", "Zakupy", "700.00"),
        ("2025-11-04", "Przychody", "Wynagrodzenie", "8000.00"),
    )
    postep = budzet.postep_celu(
        wpisy, nazwa="Poduszka", kategoria="Poduszka finansowa",
        kwota_docelowa=Decimal("10000.00"), termin=date(2026, 12, 31),
        dzis=date(2025, 12, 1))
    assert postep.uzbierane == Decimal("2500.00")
    assert postep.brakuje == Decimal("7500.00")
    assert postep.procent == Decimal("25.0")


def test_postep_celu_ignoruje_inne_kategorie_i_inne_typy():
    """Kontrola dwustronna do testu wyzej: te same dane, inny cel, inna suma.

    Bez niej "uzbierane == 2500" bylo by zielone takze wtedy, gdyby funkcja
    sumowala wszystko po kolei i przypadkiem trafila w te liczbe.
    """
    wpisy = _wpisy(
        ("2025-10-01", "Oszczędności", "Poduszka finansowa", "1000.00"),
        ("2025-11-01", "Oszczędności", "Poduszka finansowa", "1500.00"),
        ("2025-11-02", "Oszczędności", "Inwestycje", "9999.00"),
        ("2025-11-03", "Wydatki", "Zakupy", "700.00"),
    )
    postep = budzet.postep_celu(
        wpisy, nazwa="Gielda", kategoria="Inwestycje",
        kwota_docelowa=Decimal("20000.00"), termin=date(2026, 12, 31),
        dzis=date(2025, 12, 1))
    assert postep.uzbierane == Decimal("9999.00")


def test_postep_celu_powyzej_stu_procent_nie_jest_obcinany():
    """Cel przekroczony to informacja, nie blad. Obciecie do 100% ukrywa,
    ze na cel poszlo wiecej, niz mialo."""
    wpisy = _wpisy(("2025-10-01", "Oszczędności", "Inwestycje", "5000.00"))
    postep = budzet.postep_celu(
        wpisy, nazwa="Cel", kategoria="Inwestycje",
        kwota_docelowa=Decimal("4000.00"), termin=date(2026, 1, 31),
        dzis=date(2025, 12, 1))
    assert postep.procent == Decimal("125.0")
    assert postep.brakuje == Decimal("0.00")
    assert postep.osiagniety is True


def test_postep_celu_podaje_ile_odkladac_miesiecznie():
    """Cel bez tempa to zyczenie. Liczba mowi, czy termin jest realny."""
    wpisy = _wpisy(("2025-12-01", "Oszczędności", "Inwestycje", "2000.00"))
    postep = budzet.postep_celu(
        wpisy, nazwa="Cel", kategoria="Inwestycje",
        kwota_docelowa=Decimal("8000.00"), termin=date(2026, 6, 1),
        dzis=date(2025, 12, 1))
    # brakuje 6000, do terminu 6 pelnych miesiecy -> 1000 miesiecznie
    assert postep.brakuje == Decimal("6000.00")
    assert postep.miesiecy_do_terminu == 6
    assert postep.tempo_miesieczne == Decimal("1000.00")


def test_postep_celu_po_terminie_nie_dzieli_przez_zero():
    wpisy = _wpisy(("2025-10-01", "Oszczędności", "Inwestycje", "100.00"))
    postep = budzet.postep_celu(
        wpisy, nazwa="Cel", kategoria="Inwestycje",
        kwota_docelowa=Decimal("5000.00"), termin=date(2025, 9, 1),
        dzis=date(2025, 12, 1))
    assert postep.miesiecy_do_terminu == 0
    assert postep.tempo_miesieczne is None
    assert postep.po_terminie is True


def test_postep_celu_na_pustych_wpisach_daje_zero_a_nie_wyjatek():
    postep = budzet.postep_celu(
        _wpisy(), nazwa="Cel", kategoria="Inwestycje",
        kwota_docelowa=Decimal("1000.00"), termin=date(2026, 12, 31),
        dzis=date(2025, 12, 1))
    assert postep.uzbierane == Decimal("0.00")
    assert postep.procent == Decimal("0.0")


def test_saldo_dzienne_daje_jeden_punkt_na_dzien():
    """Wykres salda z jednym punktem na WPIS ma os, na ktorej ta sama data
    powtarza sie kilka razy - wyglada, jakby dni bylo wiecej, niz jest.

    Kontrola licznosci wbudowana: punktow ma byc tyle, ile UNIKALNYCH dat.
    """
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "1000.00"),
        ("2025-10-01", "Wydatki", "Zakupy", "100.00"),
        ("2025-10-01", "Wydatki", "Transport", "50.00"),
        ("2025-10-03", "Wydatki", "Zakupy", "200.00"),
    )
    punkty = budzet.saldo_dzienne(wpisy)
    assert len(punkty) == 2
    assert punkty == [("2025-10-01", Decimal("850.00")),
                      ("2025-10-03", Decimal("650.00"))]


def test_saldo_dzienne_konczy_sie_tam_gdzie_saldo_narastajace():
    """Kontrola dwustronna: agregacja po dniach nie moze zmienic wyniku koncowego."""
    wpisy = _wpisy(
        ("2025-10-01", "Przychody", "Wynagrodzenie", "8130.78"),
        ("2025-10-01", "Wydatki", "Transport", "6.00"),
        ("2025-10-05", "Wydatki", "Zakupy", "13.99"),
        ("2025-10-05", "Oszczędności", "Reszta Revolut", "2.02"),
    )
    assert budzet.saldo_dzienne(wpisy)[-1][1] == budzet.saldo_narastajaco(wpisy)[-1]


def test_saldo_dzienne_na_pustej_ramce_daje_pusta_liste():
    assert budzet.saldo_dzienne(_wpisy()) == []


# --- arytmetyka okresowa --------------------------------------------------

def test_wykonanie_planu_okres_jednomiesieczne_rowna_sie_miesiecznemu():
    """Kontrola dwustronna: refaktor nie ma prawa przesunac starych wynikow."""
    wpisy = _wpisy(("2025-10-05", "Wydatki", "Zakupy", "150.00"))
    plan = _plan((2025, 10, "Wydatki", "Zakupy", "500.00"))
    assert budzet.wykonanie_planu_okres(wpisy, plan, [(2025, 10)]) == \
        budzet.wykonanie_planu(wpisy, plan, 2025, 10)


def test_wykonanie_planu_okres_sumuje_miesiace():
    wpisy = _wpisy(("2025-10-05", "Wydatki", "Zakupy", "150.00"),
                   ("2025-11-05", "Wydatki", "Zakupy", "250.00"))
    plan = _plan((2025, 10, "Wydatki", "Zakupy", "500.00"),
                 (2025, 11, "Wydatki", "Zakupy", "500.00"))
    pozycje = budzet.wykonanie_planu_okres(wpisy, plan, [(2025, 10), (2025, 11)])
    assert len(pozycje) == 1
    assert pozycje[0].planowane == Decimal("1000.00")
    assert pozycje[0].wykonane == Decimal("400.00")
    assert pozycje[0].procent == Decimal("40.0")


def test_wykonanie_planu_okres_nie_gubi_kategorii_z_jednego_miesiaca():
    """Kontrola licznosci: kategoria obecna tylko w jednym miesiacu okresu
    ma zostac w zestawieniu, a nie wypasc na przecieciu."""
    wpisy = _wpisy(("2025-10-05", "Wydatki", "Zakupy", "150.00"))
    plan = _plan((2025, 11, "Wydatki", "Transport", "300.00"))
    pozycje = budzet.wykonanie_planu_okres(wpisy, plan, [(2025, 10), (2025, 11)])
    assert {p.kategoria for p in pozycje} == {"Zakupy", "Transport"}


def test_wydatki_wg_kategorii_okres_sumuje_miesiace():
    wpisy = _wpisy(("2025-10-05", "Wydatki", "Zakupy", "100.00"),
                   ("2025-11-05", "Wydatki", "Zakupy", "300.00"),
                   ("2025-11-06", "Wydatki", "Transport", "200.00"))
    assert budzet.wydatki_wg_kategorii_okres(
        wpisy, [(2025, 10), (2025, 11)]) == [
            ("Zakupy", Decimal("400.00")), ("Transport", Decimal("200.00"))]


# --- Z42: zestawienie widzi regule dziedziczona ---------------------------

def _plan_trwaly(*krotki) -> pd.DataFrame:
    """Ramka planu z kolumnami okresu obowiazywania (rok/miesiac = OD kiedy)."""
    return pd.DataFrame([
        {"rok": r, "miesiac": m, "typ": t, "kategoria": k,
         "kwota_planowana": Decimal(kw), "powtarzalna": 1,
         "do_roku": None, "do_miesiaca": None}
        for r, m, t, k, kw in krotki
    ])


def test_wykonanie_planu_widzi_pozycje_dziedziczona_z_wczesniejszego_miesiaca():
    """Drugi nosnik filtrowania planu (wlasne `plan[\"rok\"] == rok`) zniknal.

    Bez tego zestawienie za wrzesien pokazywaloby „brak planu" dla pozycji,
    ktora obowiazuje od stycznia — czyli dokladnie odwrotnie, niz mowi ekran.
    """
    wpisy = _wpisy(("2026-09-05", "Wydatki", "Zakupy", "80.00"))
    plan = _plan_trwaly((2026, 1, "Wydatki", "Zakupy", "200.00"))
    pozycje = budzet.wykonanie_planu(wpisy, plan, 2026, 9)
    assert len(pozycje) == 1
    assert pozycje[0].planowane == Decimal("200.00")
    assert pozycje[0].wykonane == Decimal("80.00")


def test_wykonanie_planu_nie_widzi_pozycji_jednorazowej_z_innego_miesiaca():
    """Para kontrolna: rozwijacz nie ma prawa przepuszczac wszystkiego."""
    wpisy = _wpisy(("2026-09-05", "Wydatki", "Zakupy", "80.00"))
    plan = _plan((2026, 1, "Wydatki", "Zakupy", "200.00"))
    pozycje = budzet.wykonanie_planu(wpisy, plan, 2026, 9)
    assert [p.planowane for p in pozycje] == [Decimal("0.00")]
