"""Straznicy weryfikacji stawek u zrodla.

Sedno tego modulu to normalizacja. Przy projektowaniu 2026-08-25 zmierzono
pulapke: pierwsze porownanie zglosilo "1 495,04 - BRAK" na stronie, ktora te
kwote ZAWIERA. Strona zapisuje ja jako "1495,04", bez separatora tysiecy,
i NIEKONSEKWENTNIE - obok stoi "17 940,48" ze spacja.

Pomiar nie "nie znalazl liczby". Pomiar szukal zlego napisu.
"""
from decimal import Decimal

import httpx
import pytest

from silnik.rdzen import stawki, weryfikacja


# --- normalizacja ---------------------------------------------------------

def test_normalizacja_sklejata_separator_tysiecy():
    assert "1495,04" in weryfikacja.normalizuj("<td>1 495,04 zł</td>")
    assert "1495,04" in weryfikacja.normalizuj("<td>1495,04 zł</td>")
    assert "17940,48" in weryfikacja.normalizuj("<td>17 940,48zł</td>")


def test_normalizacja_radzi_sobie_ze_spacja_nierozdzielajaca():
    """U+00A0 miedzy cyframi - dokladnie to, czego strony rzadowe uzywaja.

    Znak zapisany jawnie przez \\u00a0, a nie wklejony - wklejony bylby
    w kodzie nie do odroznienia od zwyklej spacji przy przegladzie.
    """
    assert "9228,64" in weryfikacja.normalizuj("<b>9\u00a0228,64</b>")
    assert "9228,64" in weryfikacja.normalizuj("<b>9\u202f228,64</b>")  # waska


def test_normalizacja_radzi_sobie_z_cyframi_pelnej_szerokosci():
    """Jedyny przypadek, w ktorym NFKC cokolwiek wnosi - zmierzone 2026-08-25.

    Spacje specjalne zalatwia juz `\\s`: w Pythonie dopasowuje U+00A0 i U+202F.
    Przebieg mutacyjny pokazal, ze usuniecie NFKC nie czerwieni NICZEGO -
    linia byla kodem obronnym bez straznika. Ten test istnieje po to, zeby
    dala sie zaczerwienic (CLAUDE.md par. 8 v1.17).
    """
    assert "9228" in weryfikacja.normalizuj("<b>\uff19\uff12\uff12\uff18</b>")


def test_normalizacja_nie_sklei_dwoch_osobnych_liczb():
    """Kontrola dwustronna: separator sklejamy TYLKO przed grupa dokladnie 3 cyfr.

    Bez tego warunku "12 1234" stalby sie "121234" i pomiar zaczalby widziec
    liczby, ktorych na stronie nie ma - falszywy alarm zamiast falszywego spokoju.
    """
    assert "12 1234" in weryfikacja.normalizuj("12 1234")
    assert "121234" not in weryfikacja.normalizuj("12 1234")


def test_normalizacja_usuwa_znaczniki():
    assert "<td>" not in weryfikacja.normalizuj("<td>498,35</td>")


# --- warianty zapisu kwoty ------------------------------------------------

def test_warianty_zapisu_obejmuja_kwote_bez_koncowki_zerowej():
    """Podstawa spolecznych stoi na stronie jako "5 652 zl", bez groszy."""
    w = weryfikacja.warianty_zapisu(Decimal("5652.00"))
    assert "5652,00" in w
    assert "5652" in w


# --- trzy wyjscia ---------------------------------------------------------

def _strona_ze_wszystkim():
    """Sztuczna strona z kompletem wartosci ORAZ fraz terminow z rejestru.

    Frazy doszly 2026-08-25 (Zadanie 22b): weryfikacja sprawdza juz nie tylko
    kwoty, ale i zdania niosace termin platnosci. Strona bez fraz dawalaby
    ROZBIEZNE i test przestalby mierzyc to, co mierzyl.
    """
    kawalki = []
    for wartosc in weryfikacja.oczekiwane_wartosci().values():
        for pozycja in wartosc:
            kawalki.append(f"<td>{weryfikacja.warianty_zapisu(pozycja)[0]}</td>")
    for frazy in weryfikacja.oczekiwane_frazy().values():
        for fraza in frazy:
            kawalki.append(f"<p>{fraza}</p>")
    return "".join(kawalki)


def test_sztuczna_strona_naprawde_niesie_frazy():
    """Kontrola dwustronna: strona, ktora przestala niesc frazy, dawalaby
    ROZBIEZNE i wygladalo by to jak zmiana na stronie rzadowej."""
    strona = _strona_ze_wszystkim()
    assert weryfikacja.oczekiwane_frazy(), "brak fraz do sprawdzenia"
    for frazy in weryfikacja.oczekiwane_frazy().values():
        for fraza in frazy:
            assert fraza in strona


def test_zgodne_gdy_wszystkie_wartosci_sa_na_stronie(monkeypatch, tmp_path):
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: _strona_ze_wszystkim())
    r = weryfikacja.sprawdz(cache_wazny_godzin=0)
    assert r.wynik is weryfikacja.Wynik.ZGODNE
    assert r.rozbiezne == []


def test_rozbieznosc_nie_nadpisuje_rejestru(monkeypatch, tmp_path):
    """Pobieracz, ktory przestal trafiac w liczbe, wyglada tak samo jak ten,
    ktory trafia. Dlatego mechanizm POROWNUJE, nigdy nie zapisuje."""
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: "<p>zadnych liczb</p>")
    przed = stawki.skladka_zdrowotna(Decimal("1.00"))
    r = weryfikacja.sprawdz(cache_wazny_godzin=0)
    assert r.wynik is weryfikacja.Wynik.ROZBIEZNE
    assert r.rozbiezne, "rozbieznosc bez listy pozycji jest bezuzyteczna"
    assert stawki.skladka_zdrowotna(Decimal("1.00")) == przed


def test_brak_sieci_daje_NIEDOSTEPNE_a_nie_wyjatek(monkeypatch, tmp_path):
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "cache.json")

    def wybuch(url):
        raise httpx.ConnectError("brak sieci")

    monkeypatch.setattr(weryfikacja, "_pobierz", wybuch)
    r = weryfikacja.sprawdz(cache_wazny_godzin=0)
    assert r.wynik is weryfikacja.Wynik.NIEDOSTEPNE
    assert "niepotwierdzone" in r.komunikat.lower() or "nie udało" in r.komunikat.lower()


def test_raport_zawsze_niesie_zrodla_i_date(monkeypatch, tmp_path):
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: _strona_ze_wszystkim())
    r = weryfikacja.sprawdz(cache_wazny_godzin=0)
    assert r.zrodla and all(u.startswith("https://") for u in r.zrodla)
    assert r.data is not None


# --- kontrola licznosci ---------------------------------------------------

def test_sprawdzanych_wartosci_jest_szesnascie():
    """Sprawdzenie, do ktorego nic nie dociera, melduje sukces.

    ZMIANA Z58, W TYM SAMYM COMMICIE CO SILNIK SKALI I SWIADOMIE.
    Stara nazwa i stare brzmienie, doslownie:
    `test_sprawdzanych_wartosci_jest_dziesiec` z `assert ile == 10`
    i zdaniem „Przy projektowaniu zmierzono 10/10 wartosci ZGODNE ze zrodlami".

    Z58 doklada SZESC stalych skali (`portal/00264`) jako WARUNEK UKONCZENIA
    silnika skali — bez nich drugi silnik podatkowy nie mialby zadnego pokrycia
    mechanizmem, ktory ma pierwszy. Ta liczba ma sie zmieniac razem z rejestrem
    i wlasnie po to tu stoi: 10 + 6 = 16.
    """
    ile = sum(len(v) for v in weryfikacja.oczekiwane_wartosci().values())
    assert ile == 16


# --- test sieciowy --------------------------------------------------------

@pytest.mark.siec
def test_realne_zrodla_zwracaja_ZGODNE(tmp_path, monkeypatch):
    """Odpalany osobno: pytest -m siec. Przy projektowaniu 2026-08-25: 10/10."""
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "cache.json")
    r = weryfikacja.sprawdz(cache_wazny_godzin=0)
    assert r.wynik is weryfikacja.Wynik.ZGODNE, f"rozbiezne: {r.rozbiezne}"


def test_brak_frazy_terminu_daje_rozbieznosc(monkeypatch, tmp_path):
    """LUKA WYKRYTA MUTACJA M76 (2026-08-25). Do tej chwili zaden test nie
    sprawdzal, czy `sprawdz` FAKTYCZNIE uzywa fraz — wyciecie ich z petli
    przezylo cala suite. `test_frazy_terminow_trafiaja_do_weryfikacji`
    pilnowal tylko tego, ze frazy SA NA LISCIE, nie ze ktos je czyta.

    Strona ma komplet kwot i ANI JEDNEJ frazy: gdyby frazy nie byly
    sprawdzane, wynik bylby ZGODNE.
    """
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "cache.json")
    kawalki = []
    for wartosc in weryfikacja.oczekiwane_wartosci().values():
        for pozycja in wartosc:
            kawalki.append(f"<td>{weryfikacja.warianty_zapisu(pozycja)[0]}</td>")
    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: "".join(kawalki))

    r = weryfikacja.sprawdz(cache_wazny_godzin=0)
    assert r.wynik is weryfikacja.Wynik.ROZBIEZNE
    assert any("termin" in pozycja for pozycja in r.rozbiezne), r.rozbiezne


# --- Z74: odczyt bez sieci (rozdzial rol B5) ------------------------------
#
# TRZY REGULY, TRZECH STRAZNIKOW, KAZDY NA WLASNYM PRZYPADKU (poprawka P1):
#
#   (a) brak zapisu       -> `None`          — `..._zwraca_None_gdy_NIGDY_...`
#   (b) zapis jest        -> oddaje raport   — `..._oddaje_ZAPISANY_raport`
#   (c) NIGDY nie do sieci                   — `..._NIE_dotyka_sieci`
#
# (b) jest kontrola licznosci dla (a): asercja `is None` sama z siebie
# przeszlaby takze wtedy, gdyby funkcja zawsze zwracala `None` i nigdy nic
# nie widziala.
#
# (c) STOI NA ZAPISIE PRZETERMINOWANYM, i to jest rozstrzygajace. Pierwsza
# wersja tego straznika badala przypadek BRAKU zapisu — czyli ten sam, co (a)
# — i przez to obie reguly mial ten sam strazacy przypadek: mutacja jednej
# czerwienila obie. Wariant z zapisem WAZNYM jest jeszcze gorszy i to jest
# ZMIERZONE, nie przypuszczone: przy waznym zapisie `sprawdz()` tez oddaje
# go z cache'u bez wyjscia do sieci, wiec `z_cache` i `sprawdz` sa
# NIEODROZNIALNE i mutacja „z_cache wola sprawdz" PRZECHODZI (proba
# 2026-08-27: `1 passed`).
#
# Zapis PRZETERMINOWANY rozdziela je jednoznacznie:
#   * `z_cache`  ma oddac `None` i NIE ruszyc sieci;
#   * `sprawdz`  musi w tym stanie WYJSC do sieci.
# Wtedy mutacja „brak pliku -> ZGODNE" nie rusza (c) w ogole (plik JEST),
# a mutacja „wolaj sprawdz" czerwieni (c) po liczbie wyjsc do sieci.

def test_z_cache_zwraca_None_gdy_NIGDY_nie_sprawdzano(tmp_path, monkeypatch):
    """Trzecia możliwość obok ZGODNE i ROZBIEŻNE: nie wiadomo, bo nikt
    nie pytał. Zwrócenie tu ZGODNE byłoby dobrą wiadomością bez pokrycia.

    `_pobierz` podstawione (poprawka P2) MIMO ze ten test nie mowi o sieci.
    Powod jest zmierzony: bez podstawienia mutacja „z_cache wola sprawdz"
    wypuszczala ten test do PRAWDZIWEJ sieci — 5 stron po 20 s. Przebieg
    mutacyjny ma mierzyc kod, nie lacze.

    ATRAPA ODDAJE PUSTA TRESC, NIE `pytest.fail` (poprawka W4). `pytest.fail`
    rzuca `Failed` — klase spoza `Exception` — wiec `sprawdz` jej NIE polyka
    i pod mutacja test konczyl sie WEWNATRZ `sprawdz`, nie dochodzac do
    wlasnej asercji. Czerwien meldowala wtedy zlamanie reguly SIECIOWEJ,
    ktorej ten straznik nie pilnuje ani nie opisuje — cudza regula wniesiona
    tylnymi drzwiami. Pusta tresc zostawia mu wlasna asercje, a sieci i tak
    nie rusza. Reguly sieciowej pilnuje `test_z_cache_NIE_dotyka_sieci`,
    ktory liczy wyjscia jawnie.
    """
    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: "")
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "brak.json")
    assert weryfikacja.z_cache() is None


def test_z_cache_NIE_dotyka_sieci(tmp_path, monkeypatch):
    """Pilnuje BRAKU SIECI — nie tego, ze zwracane jest `None`.

    Przypadek: zapis podreczny ISTNIEJE, ale jest PRZETERMINOWANY (starszy
    niz `wazny_godzin`). W tym stanie `z_cache` ma oddac `None` bez ani
    jednego wyjscia do sieci, a `sprawdz` MUSI do niej wyjsc — dlatego ten
    przypadek rozroznia obie funkcje, czego ani brak zapisu, ani zapis wazny
    nie robia (uzasadnienie w naglowku sekcji).
    """
    from datetime import datetime, timedelta

    wywolania: list[str] = []

    def licz_i_wybuchnij(url):
        wywolania.append(url)
        raise AssertionError(f"wyjscie do sieci po {url}")

    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "stary.json")
    monkeypatch.setattr(weryfikacja, "_pobierz", licz_i_wybuchnij)
    weryfikacja._zapisz_cache(weryfikacja.Raport(
        weryfikacja.Wynik.ZGODNE, datetime.now() - timedelta(hours=48),
        ["http://x"], [], "Zapis sprzed dwoch dob."))

    # KONTROLA LICZNOSCI, czesc pierwsza: zapis MUSI istniec. `_zapisz_cache`
    # polyka `OSError`, wiec bez tej asercji nieudany zapis zamienilby ten
    # test w kopie straznika (a) i nikt by tego nie zauwazyl.
    assert weryfikacja.SCIEZKA_CACHE.exists(), "zapis podreczny sie nie utworzyl"

    raport = weryfikacja.z_cache(wazny_godzin=24)

    # Asercja o SIECI idzie PIERWSZA — to jest regula, ktorej pilnuje ten
    # straznik, i to ona ma sie pojawic w komunikacie, gdy padnie. Odwrotna
    # kolejnosc dawala komunikat „oddal raport zamiast None", czyli cudza
    # regule (zmierzone przy powtorzeniu M349).
    assert wywolania == [], f"z_cache poszlo do sieci po: {wywolania}"
    # Zapis PRZETERMINOWANY nie jest serwowany jak swiezy.
    assert raport is None, raport

    # KONTROLA LICZNOSCI, czesc druga: przy TYM SAMYM ustawieniu `sprawdz`
    # do sieci DOCHODZI. Bez tego zdania asercja `wywolania == []` przeszlaby
    # rowniez wtedy, gdyby do pomiaru nie mialo prawa nic dotrzec.
    weryfikacja.sprawdz(cache_wazny_godzin=24)
    assert wywolania, "ustawienie testu w ogole nie dopuszcza wyjscia do sieci"


def test_z_cache_oddaje_ZAPISANY_raport(tmp_path, monkeypatch):
    """Kontrola licznosci dla straznika (a): przy ZAPISANYM raporcie funkcja
    jednak cos oddaje. Bez tego `assert ... is None` przechodzilby rowniez
    wtedy, gdyby `z_cache` nie widzialo nigdy niczego.

    `_pobierz` podstawione (poprawka P2) — audyt 2026-08-27 wykazal, ze byl
    to ostatni test Z74 bez tego zabezpieczenia.
    """
    from datetime import datetime

    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: "")
    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", tmp_path / "w.json")
    weryfikacja._zapisz_cache(weryfikacja.Raport(
        weryfikacja.Wynik.ROZBIEZNE, datetime.now(), ["http://x"],
        ["1234,00 — nie znaleziona"], "Rozbieżność."))
    raport = weryfikacja.z_cache()
    assert raport is not None
    assert raport.wynik is weryfikacja.Wynik.ROZBIEZNE
    assert raport.rozbiezne == ["1234,00 — nie znaleziona"]


# --- P3 (Z77): fikstury globalne z `conftest.py` ---------------------------
#
# Dwie fikstury `autouse` odsuwaja KAZDY test bez znacznika `siec` od sieci
# i od podrecznego zapisu czlowieka. Do Z77 istnialy w dwoch miejscach
# naraz — podstawienie `_pobierz` bylo rozsypane po pojedynczych testach
# (`monkeypatch` w kazdym z osobna), a odsuniecie `SCIEZKA_CACHE` mialo
# zasieg jednego pliku (`test_api_trasy.py`). Trzeci plik potrzebujacy
# tego samego (`test_straznik.py`, bo `przebieg.wykonaj` DOMYSLNIE wola
# `weryfikacja.sprawdz()`) bylby trzecim nosnikiem tej samej reguly.
#
# Nosnik produkcyjnej funkcji zlapany na poziomie MODULU, czyli przed
# uruchomieniem fikstur — inaczej porownanie nizej mialoby po obu stronach
# ten sam obiekt podstawiony.

_POBIERACZ_PRODUKCYJNY = weryfikacja._pobierz


def test_fikstura_globalna_ODSUWA_pobieracz_od_sieci():
    """Zaden test bez znacznika `siec` nie ma prawa dotknac sieci.

    Kontrola dwustronna: sprawdzane jest i to, ze nazwa zostala podmieniona,
    i to, ze podmiana FAKTYCZNIE wybucha przy wywolaniu. Sama pierwsza
    asercja przeszlaby takze wtedy, gdyby podstawiono funkcje, ktora
    grzecznie wychodzi do sieci.
    """
    assert weryfikacja._pobierz is not _POBIERACZ_PRODUKCYJNY, \
        "fikstura `bez_sieci` z conftest.py nie podstawila pobieracza"
    with pytest.raises(BaseException) as blad:
        weryfikacja._pobierz("https://przyklad.invalid/stawki")
    assert "siec" in str(blad.value), str(blad.value)


def test_fikstura_globalna_ODSUWA_podreczny_zapis_od_katalogu_domowego():
    """Podreczny zapis w katalogu tymczasowym, nie w `~/.cache`.

    Bez tego straznik jest ZEGAREM: prawdziwy plik ma waznosc 24 godzin,
    wiec ta sama asercja przechodzi przed polnoca i czerwieni sie po niej.
    """
    from pathlib import Path

    assert Path.home() not in weryfikacja.SCIEZKA_CACHE.parents, \
        f"podreczny zapis wskazuje na katalog czlowieka: {weryfikacja.SCIEZKA_CACHE}"
    assert weryfikacja.z_cache() is None, \
        "podreczny zapis nie zostal odsuniety — test czyta plik czlowieka"
