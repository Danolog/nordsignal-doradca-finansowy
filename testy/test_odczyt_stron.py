# -*- coding: utf-8 -*-
"""STRAZNICY ODCZYTU STAWEK ZE STRON.

Testy dziel sie na dwie grupy:
  — bez sieci: dzialaja na tekscie wzorcowym, biegna zawsze;
  — z siecią (`@pytest.mark.siec`): odpytuja zywa strone.

Tekst wzorcowy jest CYTATEM ze strony biznes.gov.pl (odczyt 2026-08-29),
nie parafraza. Parafraza sprawdzalaby, czy wyrazenie dziala na tekscie,
ktory sami napisalismy pod nie — czyli mierzylaby wlasna podloge.
"""

import datetime as dt
import re
from decimal import Decimal as D

import pytest

from wiedza.rejestr import Stawka
from wiedza.zrodla import strony

#: CYTAT ze strony, zachowane myslniki podluzne i spacje niełamliwe.
WZORCOWY = (
    "Minimalna podstawa, od której liczy się składki w 2026 roku, wynosi 5652 zł "
    ". Wysokości składek na ubezpieczenia emerytalne, rentowe, chorobowe i "
    "wypadkowe są wyrażone w procentach i wynoszą: na ubezpieczenie emerytalne – "
    "19,52% podstawy na ubezpieczenia rentowe – 8,00% podstawy na ubezpieczenie "
    "chorobowe – 2,45% podstawy na ubezpieczenie wypadkowe: stopa "
)


def _odczyt_z_tekstu(tekst, monkeypatch, url="https://przyklad"):
    monkeypatch.setattr(strony, "_tekst", lambda _u: tekst)
    return strony.odczytaj(url)


def test_liczba_bez_separatora_czytana_w_CALOSCI(monkeypatch):
    """Pulapka zlapana pomiarem 2026-08-29, nie czytaniem kodu.

    Pierwsza wersja wzorca miala gwiazdke przy grupie tysiecy i na napisie
    "5652 zl" dopasowywala "565" — podstawa skladek DZIESIECIOKROTNIE ZA
    NISKA, wygladajaca poprawnie. Gdyby to weszlo do rejestru, ZUS liczylby
    sie od 565 zl.
    """
    w = _odczyt_z_tekstu(WZORCOWY, monkeypatch)
    assert w["zus.podstawa_spolecznych"][0] == D("5652")


def test_wzorzec_liczby_SAM_W_SOBIE_bierze_wszystkie_cyfry():
    """Straznik SAMEGO wzorca liczby, bez kotwicy jednostki.

    DLACZEGO OSOBNO. Mutacja M9 (powrot gwiazdki przy grupie tysiecy) NIE
    zaczerwienila testu `test_liczba_bez_separatora_czytana_w_CALOSCI` —
    bo tamten czyta przez regule zakonczona fraza "zl", ktora zmusza
    wyrazenie do nawrotu i sama naprawia blad. Tamten test twierdzil, ze
    pilnuje wzorca, a pilnowala go kotwica jednostki.

    Ten test mierzy wzorzec bezposrednio, na napisie BEZ jednostki po
    liczbie — czyli w warunkach, w ktorych nic go nie ratuje.
    """
    m = re.search(strony.LICZBA, "5652")
    assert m and m.group(1) == "5652", (
        f"wzorzec wzial {m.group(1) if m else None!r} zamiast '5652' — "
        "grupa tysiecy urwala liczbe po trzeciej cyfrze"
    )
    # kontrola dwustronna: forma z separatorem nadal dziala
    m2 = re.search(strony.LICZBA, "1 234,56")
    assert m2 and m2.group(1) == "1 234,56"


def test_stopy_kotwicza_sie_na_NAZWIE_ubezpieczenia(monkeypatch):
    """Przestawienie akapitu nie ma prawa podmienic emerytalnej na rentowa."""
    w = _odczyt_z_tekstu(WZORCOWY, monkeypatch)
    assert w["zus.emerytalna"][0] == D("19.52")
    assert w["zus.rentowa"][0] == D("8.00")
    assert w["zus.chorobowa"][0] == D("2.45")


def test_regula_bez_trafienia_PODNOSI_BLAD_zamiast_milczec(monkeypatch):
    """Najwazniejszy straznik tego modulu.

    Zwrocenie czesciowego wyniku byloby sprawdzeniem, do ktorego nic nie
    dociera — a takie sprawdzenie MELDUJE SUKCES. Brakujaca pozycja
    wygladalaby jak 'ta stawka sie nie zmienila'.
    """
    okrojony = WZORCOWY.replace("na ubezpieczenie emerytalne – 19,52% podstawy", "")
    with pytest.raises(strony.NieUmiemOdczytac, match="zus.emerytalna"):
        _odczyt_z_tekstu(okrojony, monkeypatch)


def test_porownanie_NIE_MYLI_procentu_z_ulamkiem(monkeypatch):
    """Rejestr trzyma 0,1952, strona podaje 19,52% — to TA SAMA wartosc.

    Bez zamiany na ulamek kazde porownanie zglaszaloby rozjazd stukrotny
    i kontrola bylaby jednym nieustajacym falszywym alarmem.
    """
    w = _odczyt_z_tekstu(WZORCOWY, monkeypatch)
    w_rejestrze = [Stawka(
        klucz="zus.emerytalna", wartosc=D("0.1952"), jednostka="ulamek",
        obowiazuje_od=dt.date(2026, 1, 1), obowiazuje_do=None,
        zrodlo_url="https://biznes.gov.pl", data_odczytu=dt.date(2026, 8, 25),
        status="zatwierdzona", zatwierdzil="Darek",
        data_zatwierdzenia=dt.date(2026, 8, 29),
    )]
    rozjazdy = [r for r in strony.porownaj(w_rejestrze, w, "u")
                if r.klucz == "zus.emerytalna"]
    assert rozjazdy == [], f"zgloszony rozjazd tam, gdzie wartosci sa rowne: {rozjazdy}"


def test_zmieniona_stawka_JEST_zglaszana(monkeypatch):
    """Kontrola dwustronna do testu wyzej: straznik ma sie czerwienic na
    bledzie I nie czerwienic na poprawnym stanie."""
    w = _odczyt_z_tekstu(WZORCOWY, monkeypatch)
    stara = [Stawka(
        klucz="zus.emerytalna", wartosc=D("0.1800"), jednostka="ulamek",
        obowiazuje_od=dt.date(2026, 1, 1), obowiazuje_do=None,
        zrodlo_url="https://biznes.gov.pl", data_odczytu=dt.date(2026, 8, 25),
        status="zatwierdzona", zatwierdzil="Darek",
        data_zatwierdzenia=dt.date(2026, 8, 29),
    )]
    rozjazdy = {r.klucz for r in strony.porownaj(stara, w, "u")}
    assert "zus.emerytalna" in rozjazdy


def test_odczyt_NIE_MA_drogi_do_zapisu_w_rejestrze():
    """Modul zwraca rozjazdy i nic poza tym. Funkcja zapisujaca cokolwiek
    do rejestru byłaby droga, ktora maszyna wpisuje stawke do przelewu."""
    zakazane = [n for n in dir(strony)
                if n.startswith(("zapisz", "zatwierdz", "wpisz", "aktualizuj"))]
    assert zakazane == [], f"odczyt stron ma funkcje zapisujace: {zakazane}"


@pytest.mark.siec
def test_zywa_strona_ODDAJE_komplet_stawek():
    """Sprawdzenie, ze strona nadal ma ten uklad. Zmiana po stronie ZUS ma
    wyjsc jako czerwony test, a nie jako czujka, ktora od pol roku milczy."""
    w = strony.odczytaj("https://www.biznes.gov.pl/pl/portal/00274")
    assert set(w) == {r.klucz for r in strony.SKLADKI}
    assert w["zus.podstawa_spolecznych"][0] > D("1000")
