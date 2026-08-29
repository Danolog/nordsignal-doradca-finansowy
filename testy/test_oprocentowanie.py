"""Strazniki: oprocentowanie zobowiazania WRACA jako pole — i tylko jako pole.

ZLECENIE Darka 2026-08-28 godz. 19:38, najwezszy z trzech zakresow:
„Samo pole — zebym mogl wpisac". Kolumna, zapis, odczyt, walidacja.
ZADNEGO liczenia: bez odsetek, bez harmonogramu, bez rankingu „ktory kredyt
nadplacic". Dane maja zaczac sie zbierac, reszta to osobny plasterek.

TO JEST ODWROCENIE WCZESNIEJSZEJ DECYZJI TEGO SAMEGO CZLOWIEKA. Kolumna
istniala i zostala zdjeta 2026-08-26 (Z43) z uzasadnieniem „nie wchodzi do
zadnej liczby, wiec jest martwa". Uzasadnienie bylo trafne wtedy i przestaje
obowiazywac teraz: pole ma sluzyc ZBIERANIU danych pod plasterek, ktory je
policzy. Nosnik tamtej decyzji jest zaktualizowany, a nie zostawiony obok.

PULAPKA, ktora ta zmiana musiala rozbroic. `_ZDEJMOWANE_KOLUMNY` niosla wpis
`("zobowiazania", "oprocentowanie")`, a `_zdejmij_kolumny` biegnie PO
`_dopisz_kolumny` przy KAZDYM otwarciu bazy i jest NIEODWRACALNE. Samo
dodanie kolumny do schematu daloby wiec: kolumna powstaje, po czym ginie
razem z wpisana wartoscia — przy kazdym starcie aplikacji, po cichu.
Pilnuje tego `test_kolumna_PRZEZYWA_ponowne_otwarcie_bazy`.

PUSTE TO „NIE WIEM", ZERO TO WARTOSC (regula D11). Rozroznienie siedzi
w TYPIE (`Decimal | None` i `NULL` w bazie), nie w komentarzu — bo Alior ma
realne 0%, a Revolut 9% (`docs/doradca/2026-08-28-wiedza-wskazniki-finansow-
osobistych.md` wiersz 17). Gdyby brak danych zapisywac zerem, kredyt
nieoprocentowany bylby nieodrozninalny od kredytu, o ktory nikt nie zapytal.
"""

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from silnik.rdzen import magazyn


def _kolumny(polaczenie, tabela: str) -> set[str]:
    return {w[1] for w in polaczenie.execute(f"PRAGMA table_info({tabela})")}


@pytest.fixture
def baza(tmp_path):
    p = magazyn.polacz(tmp_path / "test.db")
    yield p
    p.close()


# --- migracja -------------------------------------------------------------

def test_kolumna_ISTNIEJE_po_otwarciu(baza):
    assert "oprocentowanie" in _kolumny(baza, "zobowiazania")


def test_wersja_schematu_PODNIESIONA(baza):
    wersja = baza.execute("PRAGMA user_version").fetchone()[0]
    assert wersja == magazyn.WERSJA_SCHEMATU
    assert magazyn.WERSJA_SCHEMATU >= 11, \
        "migracja bez podniesienia wersji nie odroznia bazy przed od bazy po"


def test_kolumna_DOKLADA_SIE_do_bazy_ktora_jej_nie_ma(tmp_path):
    """Sedno migracji: `CREATE TABLE IF NOT EXISTS` nie rusza tabeli, ktora
    JEST. Bez `_dopisz_kolumny` kolumna powstalaby wylacznie w swiezej bazie,
    a u Darka nie powstalaby nigdy."""
    sciezka = tmp_path / "stara.db"
    p = sqlite3.connect(str(sciezka))
    p.execute("CREATE TABLE zobowiazania (id INTEGER PRIMARY KEY AUTOINCREMENT,"
              " nazwa TEXT NOT NULL, kapital TEXT NOT NULL,"
              " rata_minimalna TEXT NOT NULL)")
    p.execute("INSERT INTO zobowiazania (nazwa, kapital, rata_minimalna)"
              " VALUES ('Kredyt Revolut', '51234.0', '1305.05')")
    p.execute("PRAGMA user_version = 10")
    p.commit(); p.close()

    nowe = magazyn.polacz(sciezka)
    assert "oprocentowanie" in _kolumny(nowe, "zobowiazania")
    wiersze = magazyn.wczytaj_zobowiazania(nowe)
    assert len(wiersze) == 1, "kontrola licznosci: migracja zgubila wiersz"
    assert wiersze.iloc[0]["nazwa"] == "Kredyt Revolut"
    assert wiersze.iloc[0]["oprocentowanie"] is None, \
        "istniejacy wiersz ma dostac NIE WIEM, a nie 0%"
    nowe.close()


def test_kolumna_PRZEZYWA_ponowne_otwarcie_bazy(tmp_path):
    """PULAPKA Z43. `_zdejmij_kolumny` biegnie po `_dopisz_kolumny` przy kazdym
    otwarciu i jest nieodwracalne — gdyby wpis o oprocentowaniu tam zostal,
    wartosc Darka ginelaby przy kazdym starcie aplikacji."""
    sciezka = tmp_path / "test.db"
    p = magazyn.polacz(sciezka)
    magazyn.zapisz_zobowiazanie(p, nazwa="Revolut", kapital=Decimal("51234.00"),
                                rata_minimalna=Decimal("1305.05"),
                                oprocentowanie=Decimal("9"))
    p.close()
    for _ in range(2):                       # dwa kolejne uruchomienia
        p = magazyn.polacz(sciezka)
        wiersze = magazyn.wczytaj_zobowiazania(p)
        p.close()
    assert "oprocentowanie" in _kolumny(magazyn.polacz(sciezka), "zobowiazania")
    assert len(wiersze) == 1
    assert Decimal(str(wiersze.iloc[0]["oprocentowanie"])) == Decimal("9")


# --- puste kontra zero: KONTROLA DWUSTRONNA -------------------------------

def test_PUSTE_zapisuje_sie_jako_NIE_WIEM(baza):
    magazyn.zapisz_zobowiazanie(baza, nazwa="Alior", kapital=Decimal("7034.72"),
                                rata_minimalna=Decimal("319.76"))
    w = magazyn.wczytaj_zobowiazania(baza).iloc[0]
    assert w["oprocentowanie"] is None


def test_ZERO_zapisuje_sie_jako_ZERO_a_nie_jako_brak(baza):
    """Alior ma realne 0%. Zero jest odpowiedzia, nie jej brakiem."""
    magazyn.zapisz_zobowiazanie(baza, nazwa="Alior", kapital=Decimal("7034.72"),
                                rata_minimalna=Decimal("319.76"),
                                oprocentowanie=Decimal("0"))
    w = magazyn.wczytaj_zobowiazania(baza).iloc[0]
    assert w["oprocentowanie"] is not None, "zero to NIE brak danych"
    assert Decimal(str(w["oprocentowanie"])) == Decimal("0")


def test_PUSTE_i_ZERO_daja_ROZNY_zapis(baza):
    """Sedno reguly D11 w jednym tescie: dwa wiersze, dwie rozne odpowiedzi."""
    magazyn.zapisz_zobowiazanie(baza, nazwa="bez danych",
                                kapital=Decimal("100"), rata_minimalna=Decimal("10"))
    magazyn.zapisz_zobowiazanie(baza, nazwa="nieoprocentowany",
                                kapital=Decimal("100"), rata_minimalna=Decimal("10"),
                                oprocentowanie=Decimal("0"))
    bez, zero = [w["oprocentowanie"] for _, w in
                 magazyn.wczytaj_zobowiazania(baza).iterrows()]
    assert bez is None and zero is not None, f"bez={bez!r} zero={zero!r}"


# --- walidacja ------------------------------------------------------------

def test_UJEMNE_oprocentowanie_jest_bledem(baza):
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zapisz_zobowiazanie(baza, nazwa="x", kapital=Decimal("100"),
                                    rata_minimalna=Decimal("10"),
                                    oprocentowanie=Decimal("-1"))
    assert "oprocentowanie" in str(blad.value).lower()


def test_ABSURDALNIE_WYSOKIE_oprocentowanie_jest_bledem(baza):
    """Gorna granica lapie POMYLKE POLA, nie niecodzienna stope: najczestszy
    blad to wpisanie tu kwoty raty albo kapitalu (1305,05 / 51234)."""
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zapisz_zobowiazanie(baza, nazwa="x", kapital=Decimal("100"),
                                    rata_minimalna=Decimal("10"),
                                    oprocentowanie=Decimal("1305.05"))


def test_WYSOKIE_ale_MOZLIWE_oprocentowanie_przechodzi(baza):
    """KONTROLA DWUSTRONNA granicy. Bramka, ktora odrzuca wszystko wysokie,
    odrzucilaby tez chwilowke — a to prawdziwy stan, nie pomylka."""
    magazyn.zapisz_zobowiazanie(baza, nazwa="chwilowka", kapital=Decimal("100"),
                                rata_minimalna=Decimal("10"),
                                oprocentowanie=Decimal("60"))
    w = magazyn.wczytaj_zobowiazania(baza).iloc[0]
    assert Decimal(str(w["oprocentowanie"])) == Decimal("60")


def test_zmiana_zobowiazania_te_sama_regula(baza):
    """Poprawka wiersza nie moze byc tylna furtka omijajaca walidacje."""
    zid = magazyn.zapisz_zobowiazanie(baza, nazwa="x", kapital=Decimal("100"),
                                      rata_minimalna=Decimal("10"))
    with pytest.raises(magazyn.BladMagazynu):
        magazyn.zmien_zobowiazanie(baza, zobowiazanie_id=zid, nazwa="x",
                                   kapital=Decimal("100"),
                                   rata_minimalna=Decimal("10"),
                                   oprocentowanie=Decimal("-5"))
    magazyn.zmien_zobowiazanie(baza, zobowiazanie_id=zid, nazwa="x",
                               kapital=Decimal("100"),
                               rata_minimalna=Decimal("10"),
                               oprocentowanie=Decimal("9"))
    w = magazyn.wczytaj_zobowiazania(baza).iloc[0]
    assert Decimal(str(w["oprocentowanie"])) == Decimal("9")


def test_zmiana_potrafi_WYCZYSCIC_do_nie_wiem(baza):
    """Skoro pusta wartosc jest dozwolona przy zapisie, musi byc osiagalna
    takze przy poprawce — inaczej omylkowe 0% zostaje na zawsze."""
    zid = magazyn.zapisz_zobowiazanie(baza, nazwa="x", kapital=Decimal("100"),
                                      rata_minimalna=Decimal("10"),
                                      oprocentowanie=Decimal("0"))
    magazyn.zmien_zobowiazanie(baza, zobowiazanie_id=zid, nazwa="x",
                               kapital=Decimal("100"),
                               rata_minimalna=Decimal("10"),
                               oprocentowanie=None)
    assert magazyn.wczytaj_zobowiazania(baza).iloc[0]["oprocentowanie"] is None


def test_NaN_nie_udaje_wartosci_w_warunku(baza):
    """PULAPKA, ktora ta zmiana rozbraja — i ktora dziala ODWROTNIE, niz brzmi.

    `pd.read_sql` zamienia `NULL` na `NaN`. W Pythonie `bool(float('nan'))`
    to **True**, a `bool(Decimal("0"))` to **False**. Bez normalizacji
    `if wiersz["oprocentowanie"]:` uznawaloby „nie wiem" za wartosc, a realne
    0% Aliora za brak danych — czyli dokladnie na odwrot.
    """
    magazyn.zapisz_zobowiazanie(baza, nazwa="Alior", kapital=Decimal("7034.72"),
                                rata_minimalna=Decimal("319.76"),
                                oprocentowanie=Decimal("0"))
    magazyn.zapisz_zobowiazanie(baza, nazwa="nieznane", kapital=Decimal("100"),
                                rata_minimalna=Decimal("10"))
    alior, nieznane = [w["oprocentowanie"] for _, w in
                       magazyn.wczytaj_zobowiazania(baza).iterrows()]
    assert nieznane is None, f"NULL ma wracac jako None, wraca {nieznane!r}"
    assert not isinstance(nieznane, float), "NaN przeciekl do odczytu"
    assert magazyn.oprocentowanie_z_wiersza(alior) == Decimal("0")
    assert magazyn.oprocentowanie_z_wiersza(nieznane) is None
    # Kontrola sedna: rozroznienie NIE moze opierac sie na prawdziwosci.
    assert not bool(Decimal("0")), "zalozenie testu: Decimal(0) jest falszywy"


def test_dane_Darka_oba_przypadki_naraz(baza):
    """Realne dane, oba brzegi jednoczesnie (Oliver, 2026-08-28 19:46).
    Revolut 9% i Alior 0% — drugi jest wartoscia, nie pustka."""
    magazyn.zapisz_zobowiazanie(baza, nazwa="Kredyt Revolut",
                                kapital=Decimal("51234.00"),
                                rata_minimalna=Decimal("1305.05"),
                                oprocentowanie=Decimal("9"))
    magazyn.zapisz_zobowiazanie(baza, nazwa="Kredyt Alior",
                                kapital=Decimal("7034.72"),
                                rata_minimalna=Decimal("319.76"),
                                oprocentowanie=Decimal("0"))
    wiersze = magazyn.wczytaj_zobowiazania(baza)
    assert len(wiersze) == 2, "kontrola licznosci"
    revolut, alior = [magazyn.oprocentowanie_z_wiersza(w["oprocentowanie"])
                      for _, w in wiersze.iterrows()]
    assert revolut == Decimal("9")
    assert alior == Decimal("0") and alior is not None
