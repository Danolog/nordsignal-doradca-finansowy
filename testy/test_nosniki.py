# -*- coding: utf-8 -*-
"""STRAZNICY JEDNEGO NOSNIKA.

Ten plik pilnuje trzech miejsc, w ktorych ta sama regula zyje w dwoch kopiach.
Kazda z tych kopii jest SWIADOMYM dlugiem — dopuszczonym przez CLAUDE.md §3.2
wylacznie pod warunkiem straznika I jawnego progu konsolidacji. Odlozenie bez
straznika i progu jest dlugiem ukrytym, nie decyzja.

  1. mapa ekranow: `makiety/ekrany.py` (Python) i `interfejs/lib/ekrany.ts`
     PROG: przy pierwszym dopisaniu albo przemianowaniu pozycji paska —
     wtedy `ekrany.ts` generuje sie z `ekrany.py`.
  2. paleta: `makiety/paleta.json` i `interfejs/app/paleta.css`
     PROG: nie ma — `paleta.css` JEST generowana. Ten test pilnuje, ze nikt
     jej nie poprawil recznie po wygenerowaniu.
  3. minimalny rozmiar tekstu: prog 11 pt z bramki PRD §12.2 i wartosc
     w `powloka.css`.
"""

import json
import pathlib
import re

import pytest

KATALOG = pathlib.Path(__file__).resolve().parent.parent


def _ekrany_py() -> list[tuple[str, str]]:
    import sys
    sys.path.insert(0, str(KATALOG / "makiety"))
    import ekrany  # noqa: E402
    return [(e.klucz, e.napis) for e in ekrany.PASEK]


def _ekrany_ts() -> list[tuple[str, str]]:
    tekst = (KATALOG / "interfejs" / "lib" / "ekrany.ts").read_text(encoding="utf-8")
    pasek = tekst[tekst.index("export const PASEK"):tekst.index("] as const;")]
    return re.findall(r'klucz:\s*"([^"]+)",\s*napis:\s*"([^"]+)"', pasek)


def test_mapa_ekranow_NIE_ROZJECHALA_sie_miedzy_jezykami():
    """Dwa nosniki mapy paska. Rozjazd znaczy, ze pasek pokazuje co innego
    niz makieta, a bramka odwzorowania (PRD §12.7) tego nie zlapie — bo
    porownuje zrzut z ramka, a nie ramke ze spisem."""
    assert _ekrany_ts() == _ekrany_py()


def test_ksiegowanie_NIE_JEST_pozycja_paska():
    """Decyzja Darka P-3: pasek odpowiada na 'gdzie jestem', ksiegowanie na
    'co robie'. Wsuniecie go do paska cofa te decyzje po cichu."""
    klucze = [k for k, _ in _ekrany_ts()]
    assert "ksiegowanie" not in klucze
    assert len(klucze) == 9, f"pasek ma miec dziewiec pozycji, ma {len(klucze)}"


def test_paleta_css_ZGADZA_SIE_z_paleta_json():
    """Barwa rozjechana o jeden ton wobec ramki lamie bramke odwzorowania,
    a oba pliki nadal wygladaja na zadbane."""
    paleta = json.loads((KATALOG / "makiety" / "paleta.json").read_text(encoding="utf-8"))
    css = (KATALOG / "interfejs" / "app" / "paleta.css").read_text(encoding="utf-8")
    for motyw in ("jasny", "ciemny"):
        for rola in paleta[motyw]:
            assert rola["final"] in css, (
                f"barwa {rola['final']} ({rola['rola']}, motyw {motyw}) "
                "nie dotarla do paleta.css — uruchom narzedzia/buduj-palete.mjs"
            )


def test_powloka_NIE_MA_wpisanej_recznie_barwy():
    """Kazda barwa idzie ze zmiennej. Wartosc szesnastkowa w powloce to drugi
    nosnik palety."""
    css = (KATALOG / "interfejs" / "app" / "powloka.css").read_text(encoding="utf-8")
    wpisane = re.findall(r"#[0-9A-Fa-f]{3,8}\b", css)
    assert wpisane == [], f"barwy wpisane recznie w powloce: {wpisane}"


def test_tekst_podstawowy_NIE_JEST_ponizej_progu_11pt():
    """Znalezisko Z-4 poprzednika: caly tekst na 13 px = 9,75 pt, ponizej
    progu ze standardu. Prog PRD §12.2: >= 11 pt = 14,67 px."""
    css = (KATALOG / "interfejs" / "app" / "powloka.css").read_text(encoding="utf-8")
    # Rozmiar wolno zapisac skrotem (`font: 15px/...`) albo osobna wlasciwoscia
    # (`font-size: 15px`). Poprzednie brzmienie znalo TYLKO skrot, wiec przejscie
    # na zapis rozdzielony — zrobione po to, zeby nie narzucac wysokosci wiersza,
    # ktorej ramka nie ma — czerwienilo straznika przy poprawnym kodzie.
    # To jest ROZSZERZENIE zakresu, nie oslabienie: obie formy sa teraz widziane.
    dopasowanie = re.search(r"font(?:-size)?:\s*(\d+)px", css)
    assert dopasowanie, "nie znalazlem rozmiaru tekstu podstawowego w powloce"
    px = int(dopasowanie.group(1))
    assert px * 0.75 >= 11, f"tekst podstawowy {px}px = {px * 0.75:.2f} pt, prog 11 pt"


# --- spis tras ------------------------------------------------------------

def test_cztery_operacje_P1_MAJA_swoje_trasy():
    """Bez kompletu tych tras nowy interfejs NIE MOZE wylaczyc starej zakladki
    Budzet. Poprzednie brzmienie przekazania mowilo o DWOCH operacjach i bylo
    niepelne — wykryl to Darek, nie przeglad."""
    import sys
    sys.path.insert(0, str(KATALOG))
    from api import trasy

    sciezki = {(t.metoda, t.sciezka) for t in trasy.WARUNEK_WYLACZENIA}
    for wymagana in (("POST", "/api/wpisy"),
                     ("DELETE", "/api/wpisy/{id}"),
                     ("POST", "/api/plan"),
                     ("PUT", "/api/plan/{id}"),
                     ("POST", "/api/plan/{id}/zakoncz")):
        assert wymagana in sciezki, f"brak trasy warunkujacej wylaczenie: {wymagana}"


def test_kosz_planu_KONCZY_regule_a_nie_kasuje():
    """Z-9: `usun_plan` istnieje w silniku i jest SWIADOMIE odciety od
    interfejsu. Nowa aplikacja ma to zachowanie PRZEJAC, nie 'naprawic'."""
    import sys
    sys.path.insert(0, str(KATALOG))
    from api import trasy

    kasujace = [t for t in trasy.WSZYSTKIE
                if t.metoda == "DELETE" and "/plan" in t.sciezka]
    assert kasujace == [], (
        f"trasa kasujaca pozycje planu: {kasujace}. Kosz ma KONCZYC regule "
        "od biezacego miesiaca w przod (POST /api/plan/{id}/zakoncz), "
        "nie usuwac historii."
    )
