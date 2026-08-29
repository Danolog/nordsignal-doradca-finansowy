"""Strazniki czesci budzetowej magazynu: schemat, migracja, walidacja, slownik.

Migracja `wydatki_osobiste` -> `wpisy_budzetu` jest nieodwracalna, wiec ma tu
kontrole dwustronna: osobny test stwierdza, ze fikstura NAPRAWDE wlozyla trzy
wiersze. Bez niego "przeniesiono 3 z 3" bylo by zielone takze wtedy, gdy
fikstura przestanie cokolwiek wstawiac.
"""

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import budzet, magazyn
from testy.test_magazyn import TABELE_SCHEMATU


@pytest.fixture
def p(tmp_path):
    return magazyn.zmigruj_i_polacz(tmp_path / "test.db")


def _stara_baza(sciezka, wiersze) -> None:
    """Buduje baze w schemacie SPRZED Zadania 15 - z tabela `wydatki_osobiste`.

    Celowo omija `magazyn.polacz`, bo to wlasnie ono ma te tabele wchlonac.
    """
    polaczenie = sqlite3.connect(str(sciezka))
    polaczenie.executescript("""
        CREATE TABLE wydatki_osobiste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL, kategoria TEXT NOT NULL, kwota TEXT NOT NULL
        );
    """)
    for data, kategoria, kwota in wiersze:
        polaczenie.execute(
            "INSERT INTO wydatki_osobiste (data, kategoria, kwota) VALUES (?,?,?)",
            (data, kategoria, kwota))
    polaczenie.commit()
    polaczenie.close()


TRZY_WIERSZE = [
    ("2025-10-01", "Transport", "6.00"),
    ("2025-10-02", "Zakupy", "13.99"),
    ("2025-10-03", "Kredyty", "2400.33"),
]


# --- schemat --------------------------------------------------------------

def test_powstaja_wszystkie_tabele_budzetu(p):
    """Kontrola licznosci przez ROWNOSC zbioru - dzieki temu ten sam test jest
    zarazem straznikiem skasowania `wydatki_osobiste`."""
    tabele = {w[0] for w in p.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'").fetchall()}
    assert tabele == TABELE_SCHEMATU


def test_wydatki_osobiste_nie_wraca_po_ponownym_polaczeniu(tmp_path):
    """Sedno migracji: `polacz` wykonuje `_SCHEMAT` przy KAZDYM otwarciu bazy.

    Gdyby tabela zostala w schemacie, DROP przezylby do najblizszego
    uruchomienia i wrocilaby pusta - wygladajaca jak prawdziwa.
    """
    sciezka = tmp_path / "wraca.db"
    _stara_baza(sciezka, TRZY_WIERSZE)
    magazyn.zmigruj_i_polacz(sciezka).close()
    drugie = magazyn.zmigruj_i_polacz(sciezka)
    tabele = {w[0] for w in drugie.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "wydatki_osobiste" not in tabele


# --- migracja -------------------------------------------------------------

def test_fikstura_naprawde_ma_trzy_wiersze(tmp_path):
    """Kontrola dwustronna. Bez niej test migracji jest zielony takze wtedy,
    gdy fikstura wklada zero wierszy - `0 == 0` to prawda pusta."""
    sciezka = tmp_path / "kontrola.db"
    _stara_baza(sciezka, TRZY_WIERSZE)
    polaczenie = sqlite3.connect(str(sciezka))
    assert polaczenie.execute("SELECT COUNT(*) FROM wydatki_osobiste") \
        .fetchone()[0] == 3


def test_migracja_przenosi_wiersze_z_kwotami_i_typem(tmp_path):
    sciezka = tmp_path / "migracja.db"
    _stara_baza(sciezka, TRZY_WIERSZE)
    polaczenie = magazyn.zmigruj_i_polacz(sciezka)

    wpisy = magazyn.wczytaj_wpisy(polaczenie, typ=budzet.TYP_WYDATKI)
    assert len(wpisy) == 3
    assert set(wpisy["typ"]) == {"Wydatki"}
    assert set(wpisy["kategoria"]) == {"Transport", "Zakupy", "Kredyty"}
    kwoty = sorted(wpisy["kwota"])
    assert kwoty == [Decimal("6.00"), Decimal("13.99"), Decimal("2400.33")]
    assert all(isinstance(k, Decimal) for k in kwoty)


def test_migracja_pustej_bazy_nie_melduje_sukcesu(tmp_path):
    """Zero musi byc widoczne w komunikacie, a nie schowane za wartoscia
    logiczna. Migracja, ktora nic nie przeniosla, melduje ile nic."""
    sciezka = tmp_path / "pusta.db"
    _stara_baza(sciezka, [])
    polaczenie = sqlite3.connect(str(sciezka))
    raport = magazyn.wchlon_wydatki_osobiste(polaczenie)
    assert raport.przed == 0
    assert raport.przeniesione == 0
    assert "0" in raport.komunikat
    assert "gotowe" not in raport.komunikat.lower()


def test_migracja_raportuje_trzy_liczby(tmp_path):
    sciezka = tmp_path / "raport.db"
    _stara_baza(sciezka, TRZY_WIERSZE)
    polaczenie = sqlite3.connect(str(sciezka))
    polaczenie.executescript(magazyn._SCHEMAT)
    raport = magazyn.wchlon_wydatki_osobiste(polaczenie)
    assert (raport.przed, raport.przeniesione, raport.po) == (3, 3, 3)


def test_migracja_dwa_razy_nie_duplikuje(tmp_path):
    sciezka = tmp_path / "dwa_razy.db"
    _stara_baza(sciezka, TRZY_WIERSZE)
    pierwsze = magazyn.zmigruj_i_polacz(sciezka)
    pierwsze.close()
    drugie = magazyn.zmigruj_i_polacz(sciezka)
    assert len(magazyn.wczytaj_wpisy(drugie, typ=budzet.TYP_WYDATKI)) == 3
    raport = magazyn.wchlon_wydatki_osobiste(drugie)
    assert raport.przeniesione == 0


def test_baza_z_nowsza_wersja_schematu_odmawia_zamiast_pokazac_zera(tmp_path):
    """Starszy kod na nowszej bazie odtworzylby pusta tabele i pokazal 0,00 zl.

    Cicha zla liczba jest gorsza niz odmowa - dlatego wersja schematu stoi
    w bazie i jest sprawdzana przy otwarciu.
    """
    sciezka = tmp_path / "z_przyszlosci.db"
    magazyn.zmigruj_i_polacz(sciezka).close()
    polaczenie = sqlite3.connect(str(sciezka))
    polaczenie.execute(f"PRAGMA user_version = {magazyn.WERSJA_SCHEMATU + 1}")
    polaczenie.commit()
    polaczenie.close()
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zmigruj_i_polacz(sciezka)
    assert str(magazyn.WERSJA_SCHEMATU) in str(blad.value)


# --- slownik kategorii ----------------------------------------------------

def test_zasiew_daje_komplet_kategorii_ze_slownika(p):
    """Liczby nie ma w nazwie testu ANI w asercji sumy — rozjezdzala sie przy
    kazdym dolozeniu kategorii (realnie 2026-08-25, kategoria `Podatki i ZUS`).
    Pinowane sa czesci o zewnetrznym pochodzeniu: arkusz i nasze dodatki."""
    kategorie = magazyn.wczytaj_kategorie(p)
    assert len(kategorie) == sum(
        len(v) for v in budzet.KATEGORIE_STARTOWE.values())
    assert len(kategorie[kategorie["typ"] == "Przychody"]) == 4
    assert len(kategorie[kategorie["typ"] == "Oszczędności"]) == 4
    assert len(kategorie[kategorie["typ"] == "Wydatki"]) == \
        len(budzet.WYDATKI_Z_ARKUSZA) + len(budzet.KATEGORIE_SPOZA_ARKUSZA)
    assert budzet.KATEGORIA_PODATKI in set(kategorie["nazwa"])


def test_zasiew_nie_duplikuje_przy_ponownym_polaczeniu(tmp_path):
    sciezka = tmp_path / "zasiew.db"
    magazyn.zmigruj_i_polacz(sciezka).close()
    drugie = magazyn.zmigruj_i_polacz(sciezka)
    assert len(magazyn.wczytaj_kategorie(drugie)) == sum(
        len(v) for v in budzet.KATEGORIE_STARTOWE.values())


def test_ta_sama_nazwa_w_dwoch_typach_to_dwie_pozycje(p):
    """`Inne` jest jednoczesnie kategoria przychodu i wydatku."""
    kategorie = magazyn.wczytaj_kategorie(p)
    inne = kategorie[kategorie["nazwa"] == "Inne"]
    assert len(inne) == 2
    assert set(inne["typ"]) == {"Przychody", "Wydatki"}


# --- walidacja zapisu -----------------------------------------------------

def test_licznosc_typow_do_parametryzacji():
    """Bez tego oprozniona krotka dalaby pusta, zielona parametryzacje nizej."""
    assert len(budzet.TYPY) == 3


@pytest.mark.parametrize("typ", budzet.TYPY)
def test_kazdy_z_trzech_typow_przechodzi(p, typ):
    kategoria = budzet.KATEGORIE_STARTOWE[typ][0]
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ=typ,
                        kategoria=kategoria, kwota=Decimal("100.00"))
    assert len(magazyn.wczytaj_wpisy(p, typ=typ)) == 1


@pytest.mark.parametrize("zly_typ", ["Inwestycje", "", "wydatki", "Wydatek"])
def test_typ_spoza_trzech_odrzucony(p, zly_typ):
    """Asercja celuje w komunikat WLASNIE tego straznika - wyliczenie trzech
    dozwolonych wartosci.

    Pierwsza wersja sprawdzala tylko, czy w komunikacie pada slowo "typ".
    Po wylaczeniu straznika typu wpis i tak byl odrzucany - ale przez straznik
    KATEGORII, ktorego komunikat brzmi "kategoria X nie istnieje w typie Y".
    Slowo sie zgadzalo, wiec test przechodzil, mierzac cos innego niz zakladal.
    Wykryte mutacja M1, nie czytaniem kodu.
    """
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ=zly_typ,
                            kategoria="Zakupy", kwota=Decimal("10.00"))
    komunikat = str(blad.value)
    assert all(dozwolony in komunikat for dozwolony in budzet.TYPY), komunikat


def test_kategoria_spoza_slownika_odrzucona(p):
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                            kategoria="mieszkanie", kwota=Decimal("10.00"))
    assert "mieszkanie" in str(blad.value)


def test_kategoria_z_niewlasciwego_typu_odrzucona(p):
    """`Wynagrodzenie` istnieje, ale w Przychodach - jako wydatek nie przechodzi."""
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                            kategoria="Wynagrodzenie", kwota=Decimal("10.00"))


def test_kategoria_nieaktywna_odrzucona_przy_nowym_wpisie(p):
    """Inaczej kolumna `aktywna` jest ozdoba, a dezaktywacja nic nie znaczy."""
    magazyn.ustaw_aktywnosc_kategorii(p, typ="Wydatki", nazwa="PUWIS",
                                      aktywna=False)
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                            kategoria="PUWIS", kwota=Decimal("10.00"))


# --- odczyt wpisow --------------------------------------------------------

def test_kwoty_wracaja_jako_decimal_bez_straty_grosza(p):
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                        kategoria="Zakupy", kwota=Decimal("13.99"))
    kwota = magazyn.wczytaj_wpisy(p).iloc[0]["kwota"]
    assert isinstance(kwota, Decimal)
    assert kwota == Decimal("13.99")


def test_wczytaj_wpisy_filtruje_po_typie(p):
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Przychody",
                        kategoria="Wynagrodzenie", kwota=Decimal("8000.00"))
    magazyn.zapisz_wpis(p, data=date(2025, 10, 2), typ="Wydatki",
                        kategoria="Zakupy", kwota=Decimal("100.00"))
    magazyn.zapisz_wpis(p, data=date(2025, 10, 3), typ="Oszczędności",
                        kategoria="Inwestycje", kwota=Decimal("500.00"))
    assert len(magazyn.wczytaj_wpisy(p)) == 3
    assert len(magazyn.wczytaj_wpisy(p, typ=budzet.TYP_WYDATKI)) == 1
    assert magazyn.wczytaj_wpisy(p, typ=budzet.TYP_WYDATKI) \
        .iloc[0]["kwota"] == Decimal("100.00")


def test_wczytaj_wpisy_filtruje_po_zakresie_dat(p):
    for dzien in (1, 15, 30):
        magazyn.zapisz_wpis(p, data=date(2025, 10, dzien), typ="Wydatki",
                            kategoria="Zakupy", kwota=Decimal("10.00"))
    wybrane = magazyn.wczytaj_wpisy(p, od=date(2025, 10, 10),
                                    do=date(2025, 10, 20))
    assert len(wybrane) == 1


def test_usuniecie_wpisu_zdejmuje_dokladnie_jeden(p):
    """Aplikacja budzetowa bez mozliwosci poprawienia literowki jest bezuzyteczna.

    Kontrola licznosci wbudowana: trzy wpisy wchodza, jeden znika, dwa zostaja.
    Asercja "nie ma go juz" bylaby zielona takze wtedy, gdyby kasowanie
    czyscilo cala tabele.
    """
    identyfikatory = [
        magazyn.zapisz_wpis(p, data=date(2025, 10, dzien), typ="Wydatki",
                            kategoria="Zakupy", kwota=Decimal("10.00"))
        for dzien in (1, 2, 3)
    ]
    assert len(magazyn.wczytaj_wpisy(p)) == 3

    magazyn.usun_wpis(p, wpis_id=identyfikatory[1])

    zostale = magazyn.wczytaj_wpisy(p)
    assert len(zostale) == 2
    assert set(zostale["id"]) == {identyfikatory[0], identyfikatory[2]}


def test_usuniecie_nieistniejacego_wpisu_odmawia(p):
    """Cicha zgoda na skasowanie czegos, czego nie ma, ukrywa blad w numerze."""
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.usun_wpis(p, wpis_id=99999)
    assert "99999" in str(blad.value)


# --- plan budzetu ---------------------------------------------------------

def test_plan_zapisany_i_odczytany(p):
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("1500.00"))
    plan = magazyn.wczytaj_plan(p, rok=2025, miesiac=10)
    assert len(plan) == 1
    assert plan.iloc[0]["kwota_planowana"] == Decimal("1500.00")


def test_plan_zapisany_dwa_razy_nadpisuje_nie_duplikuje(p):
    for kwota in ("1500.00", "2500.00"):
        magazyn.zapisz_plan(p, rok=2025, miesiac=12, typ="Wydatki",
                            kategoria="Zakupy", kwota_planowana=Decimal(kwota))
    plan = magazyn.wczytaj_plan(p, rok=2025, miesiac=12)
    assert len(plan) == 1
    assert plan.iloc[0]["kwota_planowana"] == Decimal("2500.00")


# --- zarzadzanie kategoriami (zakladka Ustawienia) ------------------------

def test_dodanie_kategorii_pozwala_na_wpis(p):
    magazyn.dodaj_kategorie(p, typ="Wydatki", nazwa="Wakacje")
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                        kategoria="Wakacje", kwota=Decimal("999.00"))
    assert len(magazyn.wczytaj_wpisy(p, typ=budzet.TYP_WYDATKI)) == 1


def test_dodanie_istniejacej_kategorii_odrzucone(p):
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.dodaj_kategorie(p, typ="Wydatki", nazwa="Zakupy")


def test_zmiana_nazwy_kategorii_przepisuje_wpisy_i_plan(p):
    """Sama podmiana w slowniku rozsypalaby historie: wpisy wskazywalyby na
    kategorie, ktorej juz nie ma, i wypadly by ze wszystkich zestawien."""
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                        kategoria="PUWIS", kwota=Decimal("523.30"))
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="PUWIS", kwota_planowana=Decimal("600.00"))

    magazyn.zmien_nazwe_kategorii(p, typ="Wydatki", stara="PUWIS",
                                  nowa="Woda i scieki")

    wpisy = magazyn.wczytaj_wpisy(p, typ=budzet.TYP_WYDATKI)
    assert set(wpisy["kategoria"]) == {"Woda i scieki"}
    plan = magazyn.wczytaj_plan(p, rok=2025, miesiac=10)
    assert set(plan["kategoria"]) == {"Woda i scieki"}
    nazwy = set(magazyn.wczytaj_kategorie(p, typ="Wydatki")["nazwa"])
    assert "Woda i scieki" in nazwy and "PUWIS" not in nazwy


def test_zmiana_nazwy_nie_rusza_kategorii_o_tej_samej_nazwie_w_innym_typie(p):
    """`Inne` jest w dwoch typach. Zmiana w Wydatkach nie moze tknac Przychodow."""
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Przychody",
                        kategoria="Inne", kwota=Decimal("100.00"))
    magazyn.zapisz_wpis(p, data=date(2025, 10, 2), typ="Wydatki",
                        kategoria="Inne", kwota=Decimal("50.00"))
    magazyn.zmien_nazwe_kategorii(p, typ="Wydatki", stara="Inne",
                                  nowa="Wydatki rozne")
    przychody = magazyn.wczytaj_wpisy(p, typ=budzet.TYP_PRZYCHODY)
    assert set(przychody["kategoria"]) == {"Inne"}


def test_dezaktywacja_nie_rusza_wpisow(p):
    """Kategoria znika z listy wyboru, historia zostaje w calosci."""
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                        kategoria="PUWIS", kwota=Decimal("523.30"))
    magazyn.ustaw_aktywnosc_kategorii(p, typ="Wydatki", nazwa="PUWIS",
                                      aktywna=False)
    wpisy = magazyn.wczytaj_wpisy(p, typ=budzet.TYP_WYDATKI)
    assert len(wpisy) == 1
    assert wpisy.iloc[0]["kwota"] == Decimal("523.30")
    aktywne = magazyn.wczytaj_kategorie(p, typ="Wydatki", tylko_aktywne=True)
    assert "PUWIS" not in set(aktywne["nazwa"])
    assert "PUWIS" in set(magazyn.wczytaj_kategorie(p, typ="Wydatki")["nazwa"])


def test_przywrocenie_kategorii_wraca_na_liste_wyboru(p):
    magazyn.ustaw_aktywnosc_kategorii(p, typ="Wydatki", nazwa="Praca",
                                      aktywna=False)
    magazyn.ustaw_aktywnosc_kategorii(p, typ="Wydatki", nazwa="Praca",
                                      aktywna=True)
    aktywne = magazyn.wczytaj_kategorie(p, typ="Wydatki", tylko_aktywne=True)
    assert "Praca" in set(aktywne["nazwa"])


def test_policz_wpisy_kategorii(p):
    for _ in range(4):
        magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                            kategoria="PUWIS", kwota=Decimal("130.00"))
    assert magazyn.policz_wpisy_kategorii(p, typ="Wydatki", nazwa="PUWIS") == 4
    assert magazyn.policz_wpisy_kategorii(p, typ="Wydatki", nazwa="Gaz") == 0


def test_trwale_usuniecie_tylko_kategorii_bez_wpisow(p):
    magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                        kategoria="PUWIS", kwota=Decimal("523.30"))
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.usun_kategorie_trwale(p, typ="Wydatki", nazwa="PUWIS")
    assert "1" in str(blad.value)

    magazyn.usun_kategorie_trwale(p, typ="Wydatki", nazwa="Gaz")
    assert "Gaz" not in set(magazyn.wczytaj_kategorie(p, typ="Wydatki")["nazwa"])


# --- cele oszczednosciowe -------------------------------------------------

def test_cel_zapisany_i_odczytany(p):
    magazyn.zapisz_cel(p, nazwa="Poduszka", kategoria="Poduszka finansowa",
                       kwota_docelowa=Decimal("30000.00"),
                       termin=date(2027, 12, 31))
    cele = magazyn.wczytaj_cele(p)
    assert len(cele) == 1
    assert cele.iloc[0]["kwota_docelowa"] == Decimal("30000.00")
    assert cele.iloc[0]["termin"] == "2027-12-31"


def test_cel_musi_wskazywac_kategorie_OSZCZEDNOSCI(p):
    """Cel wskazujacy kategorie wydatku liczylby postep z pieniedzy wydanych.

    To nie jest formalnosc: pasek pokazywalby, ze zbierasz na wakacje, im
    wiecej wydajesz na zakupy.
    """
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_cel(p, nazwa="Zly", kategoria="Zakupy",
                           kwota_docelowa=Decimal("1000.00"),
                           termin=date(2027, 1, 1))
    assert "Zakupy" in str(blad.value)


def test_cel_o_powtorzonej_nazwie_odrzucony(p):
    magazyn.zapisz_cel(p, nazwa="Poduszka", kategoria="Poduszka finansowa",
                       kwota_docelowa=Decimal("30000.00"),
                       termin=date(2027, 12, 31))
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_cel(p, nazwa="Poduszka", kategoria="Inwestycje",
                           kwota_docelowa=Decimal("5000.00"),
                           termin=date(2027, 12, 31))


def test_usuniecie_celu_zdejmuje_dokladnie_jeden(p):
    """Kontrola licznosci: trzy cele wchodza, jeden znika, dwa zostaja."""
    identyfikatory = [
        magazyn.zapisz_cel(p, nazwa=f"Cel {i}", kategoria="Inwestycje",
                           kwota_docelowa=Decimal("1000.00"),
                           termin=date(2027, 1, 1))
        for i in range(3)
    ]
    assert len(magazyn.wczytaj_cele(p)) == 3
    magazyn.usun_cel(p, cel_id=identyfikatory[1])
    zostale = magazyn.wczytaj_cele(p)
    assert len(zostale) == 2
    assert set(zostale["id"]) == {identyfikatory[0], identyfikatory[2]}


def test_usuniecie_nieistniejacego_celu_odmawia(p):
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.usun_cel(p, cel_id=4242)
    assert "4242" in str(blad.value)


# --- ustawienia -----------------------------------------------------------

def test_ustawienie_zapisane_i_odczytane(p):
    magazyn.ustaw_ustawienie(p, "motyw", "jasny")
    assert magazyn.odczytaj_ustawienie(p, "motyw") == "jasny"


def test_ustawienie_zapisane_dwa_razy_nadpisuje(p):
    magazyn.ustaw_ustawienie(p, "motyw", "jasny")
    magazyn.ustaw_ustawienie(p, "motyw", "ciemny")
    assert magazyn.odczytaj_ustawienie(p, "motyw") == "ciemny"
    assert p.execute("SELECT COUNT(*) FROM ustawienia").fetchone()[0] == 1


def test_brak_ustawienia_daje_wartosc_domyslna(p):
    assert magazyn.odczytaj_ustawienie(p, "czego_nie_ma", "zapasowa") == "zapasowa"


# --- dostep z wielu watkow ------------------------------------------------
# Geneza, 2026-08-25: doradca odpowiadal "problem techniczny po stronie bazy
# danych", bo SDK Gemini wykonuje narzedzia w PULI WATKOW, a sterownik sqlite3
# domyslnie odmawia uzycia polaczenia poza watkiem, w ktorym powstalo. Usterka
# nie ujawnila sie wczesniej, bo do tej pory kazde wywolanie modelu konczylo
# sie kodem 429 i do narzedzi nic nie docieralo.

def test_polaczenie_dziala_z_INNEGO_watku(p):
    """Straznik regresji: narzedzia doradcy nie biegna w watku glownym."""
    import threading
    wynik = {}

    def w_watku():
        try:
            wynik["liczba"] = len(magazyn.wczytaj_wpisy(p))
        except Exception as e:            # noqa: BLE001 - chcemy KAZDY blad
            wynik["blad"] = f"{type(e).__name__}: {e}"

    watek = threading.Thread(target=w_watku)
    watek.start()
    watek.join()

    assert "blad" not in wynik, wynik.get("blad")
    assert wynik["liczba"] == 0


def test_zapis_z_innego_watku_jest_widoczny_w_glownym(p):
    """Kontrola dwustronna: samo "nie rzucilo wyjatku" nie dowodzi, ze zapis
    doszedl. Bez tego test wyzej przechodzi takze wtedy, gdy odczyt zwraca
    pusta ramke z zupelnie innego powodu."""
    import threading

    def w_watku():
        magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                            kategoria="Zakupy", kwota=Decimal("12.34"))

    watek = threading.Thread(target=w_watku)
    watek.start()
    watek.join()

    wpisy = magazyn.wczytaj_wpisy(p)
    assert len(wpisy) == 1
    assert wpisy.iloc[0]["kwota"] == Decimal("12.34")


def test_sterownik_sqlite_jest_w_trybie_szeregowanym():
    """Zalozenie, na ktorym stoi dostep wielowatkowy - nazwane wprost.

    `check_same_thread=False` jest bezpieczne WYLACZNIE dlatego, ze modul
    sqlite3 zglasza tryb SERIALIZED (threadsafety 3): synchronizacje bierze
    na siebie sama biblioteka C. Gdyby ten warunek przestal zachodzic na
    innej maszynie, ten test powie o tym wprost, zamiast zostawic ciche
    uszkodzenie danych.
    """
    import sqlite3
    assert sqlite3.threadsafety == 3, (
        f"sqlite3.threadsafety == {sqlite3.threadsafety}, oczekiwano 3 "
        "(SERIALIZED). Przy nizszej wartosci wspoldzielenie jednego polaczenia "
        "miedzy watkami przestaje byc bezpieczne i magazyn.polacz musi "
        "otwierac osobne polaczenie na watek.")


# --- usuwanie pozycji planu -----------------------------------------------

def test_usun_plan_kasuje_dokladnie_jedna_pozycje(p):
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("500.00"))
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Transport", kwota_planowana=Decimal("300.00"))
    magazyn.usun_plan(p, rok=2025, miesiac=10, typ="Wydatki", kategoria="Zakupy")
    zostalo = magazyn.wczytaj_plan(p, rok=2025, miesiac=10)
    assert len(zostalo) == 1
    assert zostalo.iloc[0]["kategoria"] == "Transport"


def test_usun_plan_nie_rusza_tej_samej_kategorii_w_INNYM_miesiacu(p):
    """Kasowanie po samej nazwie zabraloby plan z calego roku."""
    for miesiac in (10, 11, 12):
        magazyn.zapisz_plan(p, rok=2025, miesiac=miesiac, typ="Wydatki",
                            kategoria="Zakupy", kwota_planowana=Decimal("500.00"))
    magazyn.usun_plan(p, rok=2025, miesiac=11, typ="Wydatki", kategoria="Zakupy")
    assert len(magazyn.wczytaj_plan(p)) == 2


def test_usun_plan_nieistniejacej_pozycji_jest_bledem_a_nie_cisza(p):
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("500.00"))
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.usun_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                          kategoria="Transport")
    assert len(magazyn.wczytaj_plan(p)) == 1


# --- poprawka wpisu w miejscu ---------------------------------------------

def test_zmien_wpis_NIE_tworzy_drugiego_wiersza(p):
    """Kontrola licznosci: poprawka ma zmieniac, nie dokladac."""
    numer = magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                                kategoria="Zakupy", kwota=Decimal("100.00"))
    przed = len(magazyn.wczytaj_wpisy(p))
    magazyn.zmien_wpis(p, wpis_id=numer, data=date(2025, 10, 1), typ="Wydatki",
                       kategoria="Zakupy", kwota=Decimal("250.00"))
    po = magazyn.wczytaj_wpisy(p)
    assert len(po) == przed == 1
    assert po.iloc[0]["kwota"] == Decimal("250.00")
    assert int(po.iloc[0]["id"]) == numer


def test_zmien_wpis_z_kwota_ujemna_odrzucony(p):
    numer = magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                                kategoria="Zakupy", kwota=Decimal("100.00"))
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zmien_wpis(p, wpis_id=numer, data=date(2025, 10, 1),
                           typ="Wydatki", kategoria="Zakupy",
                           kwota=Decimal("-1.00"))


def test_zmien_wpis_nieistniejacy_numer_jest_bledem(p):
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zmien_wpis(p, wpis_id=9999, data=date(2025, 10, 1),
                           typ="Wydatki", kategoria="Zakupy",
                           kwota=Decimal("10.00"))


def test_zmien_wpis_zmienia_TYP_a_z_nim_kierunek_salda(p):
    """Zmiana typu ma przeliczyc saldo, nie zostawic starego znaku."""
    numer = magazyn.zapisz_wpis(p, data=date(2025, 10, 1), typ="Wydatki",
                                kategoria="Zakupy", kwota=Decimal("100.00"))
    magazyn.zmien_wpis(p, wpis_id=numer, data=date(2025, 10, 1),
                       typ="Przychody", kategoria="Inne", kwota=Decimal("100.00"))
    wpisy = magazyn.wczytaj_wpisy(p)
    assert budzet.saldo_narastajaco(wpisy) == [Decimal("100.00")]


# --- kopiowanie planu na kolejny miesiac ----------------------------------

def test_kopiuj_plan_przenosi_wszystkie_pozycje_do_pustego_miesiaca(p):
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("500.00"))
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Transport", kwota_planowana=Decimal("300.00"))
    assert magazyn.kopiuj_plan(p, z_roku=2025, z_miesiaca=10,
                               do_roku=2025, do_miesiaca=11) == (2, 0)
    assert len(magazyn.wczytaj_plan(p, rok=2025, miesiac=11)) == 2


def test_kopiuj_plan_NIE_nadpisuje_recznej_poprawki(p):
    """Reczna poprawka jest cenniejsza niz kopia."""
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("500.00"))
    magazyn.zapisz_plan(p, rok=2025, miesiac=11, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("999.00"))
    assert magazyn.kopiuj_plan(p, z_roku=2025, z_miesiaca=10,
                               do_roku=2025, do_miesiaca=11) == (0, 1)
    docelowy = magazyn.wczytaj_plan(p, rok=2025, miesiac=11)
    assert docelowy.iloc[0]["kwota_planowana"] == Decimal("999.00")


def test_kopiuj_plan_z_pustego_miesiaca_zwraca_dwa_zera(p):
    assert magazyn.kopiuj_plan(p, z_roku=2025, z_miesiaca=1,
                               do_roku=2025, do_miesiaca=2) == (0, 0)


def test_kopiuj_plan_kontrola_licznosci_zadna_pozycja_nie_ginie(p):
    """Skopiowane + pominiete musi rownac sie liczbie pozycji w zrodle."""
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("500.00"))
    magazyn.zapisz_plan(p, rok=2025, miesiac=10, typ="Wydatki",
                        kategoria="Transport", kwota_planowana=Decimal("300.00"))
    magazyn.zapisz_plan(p, rok=2025, miesiac=11, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("999.00"))
    skopiowane, pominiete = magazyn.kopiuj_plan(
        p, z_roku=2025, z_miesiaca=10, do_roku=2025, do_miesiaca=11)
    assert skopiowane + pominiete == len(magazyn.wczytaj_plan(p, rok=2025,
                                                              miesiac=10))


# --- migracja Z42: kolumny okresu obowiazywania ---------------------------

def _baza_schemat_4(sciezka, wiersze) -> None:
    """Buduje baze w schemacie SPRZED Z42 — `plan_budzetu` bez kolumn okresu.

    Celowo omija `magazyn.polacz`, bo to wlasnie ono ma kolumny dolozyc.
    `CREATE TABLE IF NOT EXISTS` nie rusza tabeli, ktora juz jest, wiec bez
    `_DOPISYWANE_KOLUMNY` migracja wygladalaby na wykonana, a kolumny by nie bylo.
    """
    polaczenie = sqlite3.connect(str(sciezka))
    polaczenie.executescript("""
        CREATE TABLE plan_budzetu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rok INTEGER NOT NULL, miesiac INTEGER NOT NULL, typ TEXT NOT NULL,
            kategoria TEXT NOT NULL, kwota_planowana TEXT NOT NULL,
            UNIQUE(rok, miesiac, typ, kategoria)
        );
    """)
    for rok, miesiac, typ, kategoria, kwota in wiersze:
        polaczenie.execute(
            "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
            "kwota_planowana) VALUES (?,?,?,?,?)",
            (rok, miesiac, typ, kategoria, kwota))
    polaczenie.execute("PRAGMA user_version = 4")
    polaczenie.commit()
    polaczenie.close()


DWA_WIERSZE_PLANU = [
    (2025, 10, "Wydatki", "Zakupy", "500.00"),
    (2025, 11, "Wydatki", "Transport", "300.00"),
]


def test_migracja_z42_doklada_kolumny_do_istniejacej_tabeli(tmp_path):
    """Baza Darka ma juz `plan_budzetu` — kolumny musza wejsc przez ALTER TABLE."""
    sciezka = tmp_path / "schemat4.db"
    _baza_schemat_4(sciezka, DWA_WIERSZE_PLANU)
    polaczenie = magazyn.zmigruj_i_polacz(sciezka)
    kolumny = {w[1] for w in polaczenie.execute("PRAGMA table_info(plan_budzetu)")}
    assert {"powtarzalna", "do_roku", "do_miesiaca"} <= kolumny


def test_migracja_z42_nie_rusza_wierszy_sprzed_migracji(tmp_path):
    """Kontrola licznosci: dwa wiersze przed, dwa po, oba jednorazowe.

    Decyzja Darka nr 2 (2026-08-26): 41 pozycji z importu zostaje
    jednorazowych. `DEFAULT 0` jest jedynym nosnikiem tego znaczenia.
    """
    sciezka = tmp_path / "dane.db"
    _baza_schemat_4(sciezka, DWA_WIERSZE_PLANU)
    polaczenie = magazyn.zmigruj_i_polacz(sciezka)
    wiersze = polaczenie.execute(
        "SELECT rok, miesiac, kwota_planowana, powtarzalna, do_roku, "
        "do_miesiaca FROM plan_budzetu ORDER BY rok, miesiac").fetchall()
    assert len(wiersze) == len(DWA_WIERSZE_PLANU)
    assert wiersze[0] == (2025, 10, "500.00", 0, None, None)
    assert wiersze[1] == (2025, 11, "300.00", 0, None, None)


def test_migracja_z42_podnosi_wersje_schematu_bazy_do_wersji_kodu(tmp_path):
    """Niezmiennikiem jest ZGODNOSC bazy z kodem, nie konkretna liczba.

    Pierwotnie test przypinal `== 5`; przy Z43 (schemat 6) czerwienil sie na
    zmianie, ktora niczego nie psula. Liczba pinowana jest tylko po stronie
    stanu wyjsciowego (baza w wersji 4 ma zostac podniesiona).
    """
    sciezka = tmp_path / "wersja.db"
    _baza_schemat_4(sciezka, DWA_WIERSZE_PLANU)
    polaczenie = magazyn.zmigruj_i_polacz(sciezka)
    assert polaczenie.execute("PRAGMA user_version").fetchone()[0] == \
        magazyn.WERSJA_SCHEMATU
    assert magazyn.WERSJA_SCHEMATU > 4


def test_swieza_baza_tez_ma_kolumny_okresu(p):
    """Kontrola dwustronna: `_SCHEMAT` i `_DOPISYWANE_KOLUMNY` to DWA miejsca.

    Test wyzej broni bazy z danymi, ten — swiezej. Usuniecie wpisu z jednego
    z tych miejsc czerwieni dokladnie jeden z nich.
    """
    kolumny = {w[1] for w in p.execute("PRAGMA table_info(plan_budzetu)")}
    assert {"powtarzalna", "do_roku", "do_miesiaca"} <= kolumny


def test_zapisz_plan_daje_pozycje_jednorazowa(p):
    """Importer nie jest ruszany, wiec `zapisz_plan` musi zostac jednorazowy."""
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("100.00"))
    assert p.execute("SELECT powtarzalna FROM plan_budzetu").fetchone()[0] == 0


# --- Z42: reguly planu obowiazujace do odwolania ---------------------------

def _regula(polaczenie, rok, miesiac, kwota, kategoria="Zakupy"):
    return magazyn.ustal_regule_planu(
        polaczenie, rok=rok, miesiac=miesiac, typ="Wydatki",
        kategoria=kategoria, kwota_planowana=Decimal(kwota))


def _obowiazuje(polaczenie, rok, miesiac):
    """Kwota obowiazujaca w danym miesiacu — czytana ROZWIJACZEM, nie tabela.

    Zagladanie do tabeli sprawdzaloby, jak dane leza, a nie co Darek zobaczy;
    to dwie rozne rzeczy i tylko druga jest obietnica produktu.
    """
    plan = magazyn.wczytaj_plan(polaczenie)
    wybrane = budzet.plan_na_miesiac(plan, rok, miesiac)
    if wybrane.empty:
        return None
    return wybrane.iloc[0]["kwota_planowana"]


def test_ustal_regule_planu_bez_obowiazujacej_wstawia_nowa(p):
    assert _regula(p, 2026, 9, "100.00") == "nowa"
    assert _obowiazuje(p, 2026, 9) == Decimal("100.00")
    assert _obowiazuje(p, 2026, 12) == Decimal("100.00")


def test_ustal_regule_planu_w_tym_samym_miesiacu_zmienia_kwote(p):
    _regula(p, 2026, 9, "100.00")
    assert _regula(p, 2026, 9, "150.00") == "zaktualizowana"
    assert len(magazyn.wczytaj_plan(p)) == 1
    assert _obowiazuje(p, 2026, 9) == Decimal("150.00")


def test_ustal_regule_planu_pozniej_wersjonuje_i_nie_rusza_przeszlosci(p):
    """Decyzja Darka nr 3: zmiana dziala od wskazanego miesiaca W PRZOD."""
    _regula(p, 2026, 9, "100.00")
    assert _regula(p, 2026, 10, "150.00") == "zwersjonowana"
    assert _obowiazuje(p, 2026, 9) == Decimal("100.00")
    assert _obowiazuje(p, 2026, 10) == Decimal("150.00")
    assert _obowiazuje(p, 2026, 11) == Decimal("150.00")


def test_wersjonowanie_w_styczniu_zamyka_grudzien_roku_poprzedniego(p):
    """`M − 1` liczone na osi absolutnej — inaczej styczen zamykalby miesiac 0."""
    _regula(p, 2026, 11, "100.00")
    assert _regula(p, 2027, 1, "150.00") == "zwersjonowana"
    stara = p.execute(
        "SELECT do_roku, do_miesiaca FROM plan_budzetu WHERE rok = 2026").fetchone()
    assert stara == (2026, 12)
    assert _obowiazuje(p, 2026, 12) == Decimal("100.00")
    assert _obowiazuje(p, 2027, 1) == Decimal("150.00")


def test_zakoncz_plan_w_miesiacu_startu_kasuje_wiersz(p):
    _regula(p, 2026, 9, "100.00")
    assert magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                                kategoria="Zakupy") == "skasowana"
    assert len(magazyn.wczytaj_plan(p)) == 0


def test_zakoncz_plan_pozniej_zamyka_regule_od_tego_miesiaca(p):
    _regula(p, 2026, 9, "100.00")
    assert magazyn.zakoncz_plan(p, rok=2026, miesiac=11, typ="Wydatki",
                                kategoria="Zakupy") == "zamknieta"
    assert _obowiazuje(p, 2026, 10) == Decimal("100.00")
    assert _obowiazuje(p, 2026, 11) is None


def test_zakoncz_plan_bez_obowiazujacej_reguly_jest_bledem(p):
    """Cisza ukrywalaby pomylke w miesiacu — kosz mial cos skasowac i nie skasowal."""
    with pytest.raises(magazyn.BladMagazynu, match="Zakupy"):
        magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                             kategoria="Zakupy")


def test_zakoncz_plan_nie_rusza_innej_kategorii(p):
    """Kontrola licznosci: zamkniecie jednej pozycji zostawia druga nietknieta."""
    _regula(p, 2026, 9, "100.00")
    _regula(p, 2026, 9, "50.00", kategoria="Transport")
    magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                         kategoria="Zakupy")
    pozostale = budzet.plan_na_miesiac(magazyn.wczytaj_plan(p), 2026, 9)
    assert list(pozostale["kategoria"]) == ["Transport"]


def test_ustal_regule_planu_nie_rusza_pozycji_jednorazowej_z_tego_miesiaca(p):
    """41 pozycji z importu zostaje jednorazowych (decyzja nr 2) — ale gdy Darek
    ustawi na nich regule, ma ona zadzialac od tego miesiaca, a nie zaginac."""
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("100.00"))
    assert _regula(p, 2026, 9, "150.00") == "zaktualizowana"
    assert _obowiazuje(p, 2026, 10) == Decimal("150.00")


def test_regula_zamknieta_nie_jest_juz_obowiazujaca_przy_ponownym_zalozeniu(p):
    """Luka wykryta mutacja M132 (2026-08-26), nie czytaniem kodu.

    Zapytanie magazynu pomijajace warunek zamkniecia przezylo 431 testow.
    Skutek byl taki: po zakonczeniu pozycji w listopadzie dodanie jej na nowo
    w grudniu „wersjonowalo" martwa regule wrzesniowa zamiast zalozyc nowa —
    czyli kosz z Kroku 5 przebiegu recznego dalo sie cofnac przypadkiem,
    zmieniajac przy okazji historie.
    """
    _regula(p, 2026, 9, "100.00")
    magazyn.zakoncz_plan(p, rok=2026, miesiac=11, typ="Wydatki",
                         kategoria="Zakupy")
    assert _obowiazuje(p, 2026, 12) is None
    assert _regula(p, 2026, 12, "150.00") == "nowa"
    # Kontrola dwustronna: nowa regula nie ruszyla zamknietej.
    assert _obowiazuje(p, 2026, 10) == Decimal("100.00")
    assert _obowiazuje(p, 2026, 11) is None
    assert _obowiazuje(p, 2026, 12) == Decimal("150.00")


def test_zapisz_plan_melduje_ze_nadpisal_istniejaca_pozycje(p):
    """Luka wykryta mutacja M158 (2026-08-26), nie czytaniem kodu.

    `zapisz_plan` NADPISUJE z zalozenia (wiez UNIQUE, bezpieczny ponowny
    import), ale wolajacy ma prawo wiedziec, ze cos zastapil. Bez tej
    informacji interfejs mowil „Dodano pozycje planu" takze wtedy, gdy
    kasowal poprzednia kwote — realna wada zgloszona przez Darka.
    """
    assert magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                               kategoria="Kredyty",
                               kwota_planowana=Decimal("1305.05")) == "nowa"
    assert magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                               kategoria="Kredyty",
                               kwota_planowana=Decimal("319.76")) == "nadpisana"
    # Kontrola licznosci: nadpisanie zostawia JEDEN wiersz, nie dwa.
    assert len(magazyn.wczytaj_plan(p, rok=2026, miesiac=9)) == 1


# --- Z48: pozycja planu = kategoria + opis, z dniem i cyklem ---------------

def test_dwie_pozycje_w_jednej_kategorii(p):
    """Zgloszenie Darka: dwa kredyty w kategorii Kredyty, trzy rachunki za gaz.

    Pozycje rozpoznaje para KATEGORIA + OPIS — czyli to, co uzytkownik wpisuje.
    """
    for opis, kwota in (("Kredyt Revolut", "1305.05"),
                        ("Kredyt Alior", "319.76")):
        magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                            kategoria="Kredyty", opis=opis,
                            kwota_planowana=Decimal(kwota))
    plan = budzet.plan_na_miesiac(magazyn.wczytaj_plan(p), 2026, 9)
    assert len(plan) == 2
    assert sum(plan["kwota_planowana"], Decimal("0")) == Decimal("1624.81")


def test_ta_sama_pozycja_zapisana_dwa_razy_nie_duplikuje_sie(p):
    """Kontrola dwustronna: rozne opisy to rozne pozycje, ten sam opis to
    ta sama pozycja. Na tym stoi bezpieczenstwo ponownego importu."""
    for _ in range(2):
        magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                            kategoria="Kredyty", opis="Kredyt Alior",
                            kwota_planowana=Decimal("319.76"))
    assert len(magazyn.wczytaj_plan(p, rok=2026, miesiac=9)) == 1


def test_dzien_miesiaca_zapisuje_sie_przy_pozycji(p):
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                        kategoria="Czesne", opis="Czesne za studia",
                        kwota_planowana=Decimal("660.00"), dzien=15)
    assert magazyn.wczytaj_plan(p).iloc[0]["dzien"] == 15


def test_dzien_spoza_miesiaca_jest_bledem(p):
    with pytest.raises(magazyn.BladMagazynu, match="dnia miesiąca"):
        magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                            kategoria="Czesne", opis="x",
                            kwota_planowana=Decimal("1.00"), dzien=32)


def test_rachunek_co_dwa_miesiace_omija_co_drugi(p):
    """Wrzesien tak, pazdziernik nie, listopad tak."""
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                        kategoria="Gaz", opis="Rachunek za gaz",
                        kwota_planowana=Decimal("400.00"),
                        powtarzalna=1, co_ile_miesiecy=2)
    plan = magazyn.wczytaj_plan(p)
    assert len(budzet.plan_na_miesiac(plan, 2026, 9)) == 1
    assert budzet.plan_na_miesiac(plan, 2026, 10).empty
    assert len(budzet.plan_na_miesiac(plan, 2026, 11)) == 1


def test_cykl_dwumiesieczny_przechodzi_przez_nowy_rok(p):
    """Start listopad 2026, co dwa miesiace: grudzien NIE, styczen 2027 TAK."""
    magazyn.zapisz_plan(p, rok=2026, miesiac=11, typ="Wydatki",
                        kategoria="Gaz", opis="Gaz",
                        kwota_planowana=Decimal("400.00"),
                        powtarzalna=1, co_ile_miesiecy=2)
    plan = magazyn.wczytaj_plan(p)
    assert budzet.plan_na_miesiac(plan, 2026, 12).empty
    assert len(budzet.plan_na_miesiac(plan, 2027, 1)) == 1


def test_cykl_krotszy_niz_miesiac_jest_bledem(p):
    with pytest.raises(magazyn.BladMagazynu, match="miesi"):
        magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                            kategoria="Gaz", opis="x",
                            kwota_planowana=Decimal("1.00"),
                            powtarzalna=1, co_ile_miesiecy=0)


def test_zmiana_kwoty_dotyczy_JEDNEJ_pozycji_a_nie_calej_kategorii(p):
    """Bez tego zmiana raty Revolutu przestawilaby takze rate Aliora."""
    for opis, kwota in (("Kredyt Revolut", "1305.05"),
                        ("Kredyt Alior", "319.76")):
        magazyn.ustal_regule_planu(p, rok=2026, miesiac=9, typ="Wydatki",
                                   kategoria="Kredyty", opis=opis,
                                   kwota_planowana=Decimal(kwota))
    magazyn.ustal_regule_planu(p, rok=2026, miesiac=10, typ="Wydatki",
                               kategoria="Kredyty", opis="Kredyt Revolut",
                               kwota_planowana=Decimal("1400.00"))
    pazdziernik = budzet.plan_na_miesiac(magazyn.wczytaj_plan(p), 2026, 10)
    kwoty = dict(zip(pazdziernik["opis"], pazdziernik["kwota_planowana"]))
    assert kwoty == {"Kredyt Revolut": Decimal("1400.00"),
                     "Kredyt Alior": Decimal("319.76")}


def test_kosz_dotyczy_JEDNEJ_pozycji(p):
    for opis, kwota in (("Kredyt Revolut", "1305.05"),
                        ("Kredyt Alior", "319.76")):
        magazyn.ustal_regule_planu(p, rok=2026, miesiac=9, typ="Wydatki",
                                   kategoria="Kredyty", opis=opis,
                                   kwota_planowana=Decimal(kwota))
    magazyn.zakoncz_plan(p, rok=2026, miesiac=10, typ="Wydatki",
                         kategoria="Kredyty", opis="Kredyt Revolut")
    pazdziernik = budzet.plan_na_miesiac(magazyn.wczytaj_plan(p), 2026, 10)
    assert list(pazdziernik["opis"]) == ["Kredyt Alior"]


def test_migracja_z48_zachowuje_wszystkie_wiersze(tmp_path):
    """Przebudowa tabeli NIE MOZE zgubic ani jednego wiersza — kontrola
    licznosci przed i po, plus wartosci domyslne nowych kolumn."""
    sciezka = tmp_path / "przed_z48.db"
    _baza_schemat_4(sciezka, DWA_WIERSZE_PLANU)
    polaczenie = magazyn.zmigruj_i_polacz(sciezka)
    wiersze = polaczenie.execute(
        "SELECT rok, miesiac, kategoria, kwota_planowana, opis, dzien, "
        "co_ile_miesiecy FROM plan_budzetu ORDER BY rok, miesiac").fetchall()
    assert len(wiersze) == len(DWA_WIERSZE_PLANU)
    assert wiersze[0] == (2025, 10, "Zakupy", "500.00", "", None, 1)


# --- Z50: kasowanie pozycji — ten miesiac czy takze przyszle ---------------

def _co_miesiac(polaczenie, opis="Energia", od=(2026, 9), kwota="165.00",
                co_ile=1):
    rok, miesiac = od
    magazyn.ustal_regule_planu(polaczenie, rok=rok, miesiac=miesiac,
                               typ="Wydatki", kategoria="Energia Elektryczna",
                               opis=opis, kwota_planowana=Decimal(kwota),
                               co_ile_miesiecy=co_ile)


def _obowiazuje_w(polaczenie, rok, miesiac) -> bool:
    return not budzet.plan_na_miesiac(
        magazyn.wczytaj_plan(polaczenie), rok, miesiac).empty


def test_kasowanie_ten_i_nastepne_konczy_regule_na_zawsze(p):
    """Domyslne dzialanie kosza: pozycja znika z tego miesiaca i z przyszlych,
    a miesiace wczesniejsze zostaja nietkniete."""
    _co_miesiac(p, od=(2026, 9))
    magazyn.zakoncz_plan(p, rok=2026, miesiac=10, typ="Wydatki",
                         kategoria="Energia Elektryczna", opis="Energia",
                         zakres="ten_i_nastepne")
    assert _obowiazuje_w(p, 2026, 9) is True
    assert _obowiazuje_w(p, 2026, 10) is False
    assert _obowiazuje_w(p, 2026, 12) is False


def test_kasowanie_TYLKO_TEGO_miesiaca_zostawia_przyszle(p):
    """Zadanie Darka 2026-08-26: „czy chce skasowac tylko ten wpis, czy
    rowniez wszystkie przyszle". Pominiecie jednego miesiaca to nie to samo
    co zakonczenie reguly."""
    _co_miesiac(p, od=(2026, 9))
    magazyn.zakoncz_plan(p, rok=2026, miesiac=10, typ="Wydatki",
                         kategoria="Energia Elektryczna", opis="Energia",
                         zakres="tylko_ten")
    assert _obowiazuje_w(p, 2026, 9) is True
    assert _obowiazuje_w(p, 2026, 10) is False
    assert _obowiazuje_w(p, 2026, 11) is True, "przyszle mialy zostac"
    assert _obowiazuje_w(p, 2026, 12) is True


def test_pominiecie_miesiaca_startowego_przesuwa_regule_na_nastepny(p):
    """Pominiecie miesiaca, w ktorym regula sie zaczyna, nie ma jej kasowac —
    ma ja przesunac."""
    _co_miesiac(p, od=(2026, 9))
    magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                         kategoria="Energia Elektryczna", opis="Energia",
                         zakres="tylko_ten")
    assert _obowiazuje_w(p, 2026, 9) is False
    assert _obowiazuje_w(p, 2026, 10) is True


def test_pominiecie_zachowuje_rytm_co_dwa_miesiace(p):
    """Rachunek co dwa miesiace po pominieciu wraca po DWOCH miesiacach,
    a nie po jednym — inaczej pominiecie przestawialoby caly cykl."""
    _co_miesiac(p, od=(2026, 9), co_ile=2)          # wrzesien, listopad, styczen
    assert _obowiazuje_w(p, 2026, 11) is True
    magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                         kategoria="Energia Elektryczna", opis="Energia",
                         zakres="tylko_ten")
    assert _obowiazuje_w(p, 2026, 9) is False
    assert _obowiazuje_w(p, 2026, 10) is False, "cykl dwumiesieczny sie nie zmienil"
    assert _obowiazuje_w(p, 2026, 11) is True


def test_pominiecie_pozycji_jednorazowej_po_prostu_ja_kasuje(p):
    """Pozycja bez powtorzen nie ma „przyszlych", wiec nie ma czego zostawiac."""
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                        kategoria="Energia Elektryczna", opis="Jednorazowa",
                        kwota_planowana=Decimal("165.00"))
    assert magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                                kategoria="Energia Elektryczna",
                                opis="Jednorazowa",
                                zakres="tylko_ten") == "skasowana"
    assert len(magazyn.wczytaj_plan(p)) == 0


def test_domyslny_zakres_kasowania_jest_ten_i_nastepne(p):
    """Kontrola dwustronna: wolanie bez `zakres` zachowuje sie jak dotad."""
    _co_miesiac(p, od=(2026, 9))
    magazyn.zakoncz_plan(p, rok=2026, miesiac=10, typ="Wydatki",
                         kategoria="Energia Elektryczna", opis="Energia")
    assert _obowiazuje_w(p, 2026, 11) is False


def test_nieznany_zakres_kasowania_jest_bledem(p):
    """Literowka w nazwie zakresu nie ma prawa cicho skasowac calej reguly."""
    _co_miesiac(p, od=(2026, 9))
    with pytest.raises(magazyn.BladMagazynu, match="zakres"):
        magazyn.zakoncz_plan(p, rok=2026, miesiac=9, typ="Wydatki",
                             kategoria="Energia Elektryczna", opis="Energia",
                             zakres="wszystkie")
