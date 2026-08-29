# -*- coding: utf-8 -*-
"""Buduje CALY projekt makiet „Doradca Finansowy" z plikow zrodlowych `*-zrodlo.dc.html`.

NOSNIK PRZENIESIONY Z `../AI CFO/docs/makiety-v2/buduj-makiety.py` (2026-08-29, zadanie Z3,
Mila). Ten projekt ma WLASNA kopie generatora — `paleta.json` i `ekrany.py` w tym katalogu
juz zakladaly jego istnienie tutaj („Skrypt `buduj-makiety.py` wczytuje ten plik", `paleta.json`
pole `opis`), ale sam plik zostal w AI CFO przy kopiowaniu 41 ramek do tego repozytorium
(commit „Doradca: fundament wciagniety do repozytorium"). Bramka `--kontrola` na tym plikw
potwierdzila przy przeniesieniu: 21 z 21 plikow zgodnych z tym, co ten skrypt produkuje —
port jest wierny zrodlu, nie nowym pismem.

DWIE RZECZY SWIADOMIE NIE PRZENIESIONE, i to jest jawny dlug, nie przeoczenie:
  - synchronizacja z dokumentem `decyzje-projektowe.md` (funkcje `tabela_palety`,
    `blok_ekranow`, `_kontrola_dokumentu`, flagi `--paleta`/`--ekrany`) — ten dokument jest
    w tym projekcie ARCHIWALNY (`CLAUDE.md` sekcja 5), nie zywym nosnikiem uzupelnianym stad;
  - `--kanwa` (zapis strony „Ekrany" do `canvas.json`) — poza zakresem zadania Z3, `canvas.json`
    tego projektu nie byl dotykany.
  Gdyby ktos potrzebowal ktoregos z nich pozniej, punkt wyjscia jest w `AI CFO/docs/makiety-v2/
  buduj-makiety.py` (wersja z 2026-08-28) — tamten plik ZOSTAJE uruchamialny, nietkniety.

DWIE RODZINY WYJSCIA, i to rozroznienie jest istotne:

  1. JEZYK OSTATECZNY — to jest projekt. Powstaje z `paleta.json`, ktory jest
     JEDYNYM nosnikiem palety obowiazujacej. Zmiana barwy = zmiana w tamtym
     pliku, nigdy tutaj.
       Main.dc.html            <- Main-zrodlo.dc.html
       CoMnieCzeka.dc.html     <- CoMnieCzeka-zrodlo.dc.html
       Main-Dobrze.dc.html     <- Main-Dobrze-zrodlo.dc.html
       NieWiem.dc.html         <- NieWiem-zrodlo.dc.html
       TrzyStany.dc.html       <- TrzyStany-zrodlo.dc.html
       Main-Ciemny.dc.html     <- Main-zrodlo.dc.html (paleta ciemna)
       TrzyStany-Ciemny.dc.html<- TrzyStany-zrodlo.dc.html (paleta ciemna)
       + siedem ekranow dolozonych 2026-08-28 (Miesiac, Budzet, Raporty, Firma, Majatek,
         Godziny, Ustawienia, Doradca) + Ksiegowanie + Miesiac-Ciemny

  2. KIERUNKI ODRZUCONE — to jest SLAD WYBORU, nie projekt. Ich barwy sa
     ZAMROZONE w tym pliku (`PALETA_PAPIER_ZAMROZONA`, `PALETA_GRANAT_ZAMROZONA`)
     i celowo NIE ida za `paleta.json`. Gdyby szly, kanwa przestalaby pokazywac,
     miedzy czym Darek wybieral — a to jedyny powod, dla ktorego te pliki zyja.
       Main-B.dc.html · Main-Papier.dc.html
       Main-Papier-Granat.dc.html · Main-Papier-Jasny.dc.html

CO PILNUJA ASERCJE:
  - kazda podmiana MUSI trafic — inaczej powstaje wariant-atrapa, ktory niczym
    sie nie rozni, a plik i tak sie zapisuje;
  - po przejsciu na jezyk ostateczny w pliku NIE MOZE zostac ani jedna barwa
    zrodlowa — kontrola dwustronna, bo sama obecnosc nowej barwy nie dowodzi,
    ze stara znikla wszedzie;
  - wlokno papieru MUSI byc cieple i NIE MOZE niesc zadnej barwy atramentu;
  - pasek nawigacji jest CO DO ZNAKU identyczny na kazdym ekranie, ktory go dostaje.

URUCHOMIENIE (z katalogu, w ktorym lezy ten plik):
    python3 buduj-makiety.py            # zapisuje 21 plikow .dc.html
    python3 buduj-makiety.py --kontrola # tylko sprawdza zgodnosc z repozytorium
"""
import hashlib
import json
import pathlib
import re
import sys
from urllib.parse import quote

KAT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KAT))
import ekrany  # noqa: E402  — jeden nosnik mapy ekranow, patrz `ekrany.py`
import wlokno  # noqa: E402  — generator faktury SVG, patrz `wlokno.py`

PALETA = json.loads((KAT / "paleta.json").read_text(encoding="utf-8"))
MAPA_JASNA = {p["zrodlo"]: p["final"] for p in PALETA["jasny"]}
MAPA_CIEMNA = {p["zrodlo_jasne"]: p["final"] for p in PALETA["ciemny"]}
WLOKNO_CIEMNE = PALETA["faktura"]["wlokno_ciemne"]
WLOKNO_JASNE = PALETA["faktura"]["wlokno_jasne"]
KAFEL_WYKRESU = PALETA["kafel_wykresu"]
KAFEL_WYKRESU_CIEMNY = PALETA["kafel_wykresu_ciemny"]

PAPIER_FINAL = MAPA_JASNA["#F5EEE0"]
ATRAMENT_FINAL = MAPA_JASNA["#2E2A22"]
POLE_FINAL = MAPA_JASNA["#FBF6EA"]
TLO_CIEMNE = MAPA_CIEMNA["#F5EEE0"]
ATRAMENT_CIEMNY_FINAL = MAPA_CIEMNA["#2E2A22"]

#: Faktura: dwa pasma czestotliwosci, kazde jako PARA warstw (ciemna + jasna),
#: zeby papier i przygasal, i rozjasnial.
PASMA = [
    # bfx,  bfy, oktawy, amp_ciemna, amp_jasna, ziarno_c, ziarno_j, barwa_c, barwa_j
    (0.05, 0.16, 3, 0.14, 0.30, 3, 17, WLOKNO_CIEMNE, WLOKNO_JASNE),      # wlokno
    (0.14, 0.20, 2, 0.0896, 0.192, 29, 41, WLOKNO_CIEMNE, WLOKNO_JASNE),  # ziarno
]


def podmien(tekst, stare, nowe, opis):
    """Podmiana z asercja. Bez asercji cichy brak trafienia daje wariant-atrape."""
    wynik = tekst.replace(stare, nowe)
    assert wynik != tekst, f"podmiana nie trafila: {opis}"
    return wynik


BARWA_RE = re.compile(r"#[0-9A-Fa-f]{8}|#[0-9A-Fa-f]{6}")


def barwy(tekst):
    """Zbior barw szesnastkowych w pliku. Faktura siedzi w adresie danych
    z barwami zakodowanymi jako `%23...`, wiec to sito jej nie widzi — i dobrze,
    bo faktura ma wlasnego straznika w `nalozy_fakture`."""
    return {b.upper() for b in BARWA_RE.findall(tekst)}


def przemaluj(tekst, mapa, opis):
    """Podmiana calej palety, z kontrola DWUSTRONNA na zbiorach barw.

    Slabsza wersja tej kontroli — „czy nowa barwa jest w pliku" — nie dowodzi
    niczego: barwa moze wejsc w jednym miejscu i zostac stara w pieciu innych,
    a plik i tak sie zapisze. Dlatego sprawdzam zbiory:
      PRZED  — w zrodle nie moze byc barwy spoza palety zrodlowej (zrodlo sie
               rozjechalo albo ktos dopisal barwe recznie, poza nosnikiem);
      PO     — w wyniku nie moze zostac barwa spoza palety ostatecznej.
    """
    dozwolone_przed = {k.upper() for k in mapa}
    obce = barwy(tekst) - dozwolone_przed
    assert not obce, f"{opis}: barwy spoza palety zrodlowej: {sorted(obce)}"
    wynik = tekst
    for stara, nowa in mapa.items():
        if stara != nowa:
            wynik = re.sub(stara, nowa, wynik, flags=re.IGNORECASE)
    dozwolone_po = {v.upper() for v in mapa.values()}
    zostaly = barwy(wynik) - dozwolone_po
    assert not zostaly, f"{opis}: barwy zrodlowe przetrwaly podmiane: {sorted(zostaly)}"
    return wynik


def nalozy_fakture(tekst, papier, atrament, mapa_atramentu):
    """Zamienia plaskie tlo korzenia na tlo z faktura SVG i sprawdza, co w niej jest."""
    tlo = wlokno.tlo(papier, PASMA, kafel=480)
    wynik = podmien(
        tekst,
        f'<div style="background: {papier}; color: {atrament}; min-height:',
        f'<div style="{tlo} color: {atrament}; min-height:',
        "tlo papieru z faktura")
    assert wynik.count("feTurbulence") == 4, \
        f"pasm faktury: {wynik.count('feTurbulence')}, ma byc 4"
    # Wlokno NIE MOZE isc za atramentem — zostaje cieple we wszystkich wariantach.
    faktura = wynik[wynik.index("data:image/svg"):wynik.index("'); background-repeat")]
    for rola, barwa in (("ciemne", WLOKNO_CIEMNE), ("jasne", WLOKNO_JASNE)):
        assert quote(barwa, safe="") in faktura or barwa.replace("#", "%23") in faktura, \
            f"wlokno {rola} nie ma barwy {barwa} — czy nie poszlo za atramentem?"
    for barwa in mapa_atramentu:
        assert barwa.replace("#", "%23").upper() not in faktura.upper(), \
            f"barwa atramentu {barwa} weszla do faktury — wlokno ma zostac cieple"
    return wynik


# ===========================================================================
# JEZYK OSTATECZNY
# ===========================================================================

ETYKIETY_WZORNIKA = {
    "jasny": (
        ("czerwień #791B1B · 7,12:1 na papierze",
         "czerwień #791B1B · 7,67:1 w najciemniejszym punkcie faktury"),
        ("zieleń #234017 · 6,54:1 na papierze",
         "zieleń #234017 · 8,39:1 w najciemniejszym punkcie faktury"),
        ("atrament cichy #4A5267 · 5,21:1 na papierze",
         "atrament cichy #4A5267 · 5,66:1 w najciemniejszym punkcie faktury"),
    ),
    "ciemny": (
        ("czerwień #E0887C · 7,12:1 na papierze", "czerwień #E0887C · 6,53:1 na tle"),
        ("zieleń #88A976 · 6,54:1 na papierze", "zieleń #88A976 · 6,53:1 na tle"),
        ("atrament cichy #9F9DAA · 5,21:1 na papierze", "atrament cichy #9F9DAA · 6,44:1 na tle"),
    ),
}


def _wspolne(t, gap_34):
    if gap_34:
        t = podmien(
            t,
            'style="width: 1040px; display: flex; flex-direction: column; gap: 40px;"',
            'style="width: 1040px; display: flex; flex-direction: column; gap: 34px;"',
            "odstep miedzygrupowy 40 -> 34 px")
    return t


def _kafel(t, barwa):
    return podmien(
        t, STARY_BLOK,
        f'<div style="display: flex; flex-direction: column; gap: 6px; '
        f'background: {barwa}; padding: 12px 20px 10px; margin: 0 -20px 8px;">',
        "kafel pod wykresem")


def _wzornik(t, motyw):
    for stare, nowe in ETYKIETY_WZORNIKA[motyw]:
        t = podmien(t, stare, nowe, f"etykieta wzornika ({motyw}): {stare}")
    return t


# ===========================================================================
# PASEK NAWIGACJI (M2) — jeden zapis, ten sam na kazdym ekranie
# ===========================================================================
#
# ZNAK SLOWNY „FINANSE" (2026-08-29, Z3, Mila) — zastapil „AI CFO" (D-47).
# NIE „Doradca Finansowy" (213,2 px, nie miesci sie — pomiar Jacka) i NIE „Doradca"
# (koliduje z pozycja paska „Doradca", ktora jest INNYM ekranem — pytania o pieniadze
# wlasnymi slowami, `ekrany.PASEK`). „Finanse" jest jedynym slowem z nazwy produktu,
# ktore (a) nie zderza sie z zadna pozycja paska, (b) miesci sie w budzecie wiersza
# naglowka z zapasem: pelny wiersz (znak + ksiegowanie + pasek dziewieciu pozycji +
# wskaznik daty Z-29) to 1360 px dostepnego miejsca; przy 0,12 em swiatla (to samo,
# co juz niesie kazda pozycja paska — `miara.SWIATLO_POZYCJI`, zaden nowy token)
# znak zajmuje 78,4 px, budzet po odjeciu reszty wiersza to ok. 83,8 px — zapas
# ok. 5,4 px (`miara.py`, pomiar 2026-08-29). Swiatlo 0,16 em (jak przy „AI CFO")
# dawaloby 82,6 px — zapas juz < 1,5 px, za blisko granicy bledu pomiaru
# (dokumentacja `miara.py`: „roznica wobec przegladarki nie przekracza jednego
# kroku swiatla"). Stad zmiana swiatla obok zmiany slowa, nie sama zmiana slowa.
ZNAK_I_ODSTEP = (
    '<span style="font-size: 15px; font-weight: 700; letter-spacing: 0.12em; '
    'text-transform: uppercase;">FINANSE</span>\n'
    '      <span style="flex: 1;"></span>')

STARA_W_NAGLOWKU = (
    '\n      <a href="#" style="min-height: 44px; display: flex; '
    'align-items: center; padding: 0 16px; font-size: 15px; color: #2E2A22; '
    'background: #FBF6EA; border: 1px solid #8F8268; border-radius: 3px; '
    'text-decoration: none;">Stara aplikacja</a>')

NAPISY_KSIEGOWANIA_W_STOPCE = ("Księgowanie — dopisz wydatek albo przychód",
                               "Księgowanie")

ODSYLACZ_STOPKI = ('<a href="#" style="min-height: 44px; display: flex; '
                   'align-items: center; font-size: 15px; color: #6B6252; '
                   'text-decoration: none;">{}</a>')

MOTYW_W_NAGLOWKU = (
    '\n      <button type="button" style="min-height: 44px; padding: 0 16px; '
    'font: inherit; font-size: 15px; color: #2E2A22; background: #FBF6EA; '
    'border: 1px solid #8F8268; border-radius: 3px; cursor: pointer;">'
    'Motyw ciemny</button>')


def _ksiegowanie(czynna):
    tlo = "#2E2A22" if czynna else "#FBF6EA"
    napis = "#F5EEE0" if czynna else "#2E2A22"
    obrys = "#2E2A22" if czynna else "#8F8268"
    kreska = "#F5EEE0" if czynna else "#6B6252"
    waga = "600" if czynna else "400"
    biezacy = ' aria-current="page"' if czynna else ""
    return (f'<a href="#"{biezacy} style="min-height: 44px; '
            f'display: inline-flex; align-items: center; gap: 8px; '
            f'padding: 0 16px; font-size: 15px; font-weight: {waga}; '
            f'color: {napis}; background: {tlo}; border: 1px solid {obrys}; '
            f'border-radius: 3px; text-decoration: none;">'
            f'<svg width="16" height="16" viewBox="0 0 16 16" fill="none" '
            f'aria-hidden="true">'
            f'<path d="M8 3.5v9M3.5 8h9" stroke="{kreska}" stroke-width="1.6" '
            f'stroke-linecap="round"></path></svg>'
            f'<span>Księgowanie</span></a>')


def _pozycja_paska(ekran, aktywna):
    czynna = ekran.klucz == aktywna
    barwa = ATRAMENT_ZRODLOWY if czynna else CICHY_ZRODLOWY
    kreska = ATRAMENT_ZRODLOWY if czynna else "transparent"
    waga = "600" if czynna else "400"
    biezacy = ' aria-current="page"' if czynna else ""
    return (f'<a href="#"{biezacy} style="min-height: 44px; '
            f'display: inline-flex; align-items: center; padding: 0 12px; '
            f'font-size: 13px; font-weight: {waga}; letter-spacing: 0.12em; '
            f'text-transform: uppercase; color: {barwa}; '
            f'text-decoration: none; border-bottom: 2px solid {kreska};">'
            f'{ekran.napis}</a>')


ATRAMENT_ZRODLOWY = "#2E2A22"
CICHY_ZRODLOWY = "#6B6252"

WSKAZNIK_DZIEN = "6 października 2026"
WSKAZNIK_GODZINA = "09:40"


def wskaznik_daty():
    return (f'<span style="font-size: 13px; color: {CICHY_ZRODLOWY}; '
            f'font-variant-numeric: tabular-nums; white-space: nowrap;">'
            f'{WSKAZNIK_DZIEN} · {WSKAZNIK_GODZINA}</span>')


def pasek_nawigacji(aktywna):
    pozycje = "".join(_pozycja_paska(e, aktywna) for e in ekrany.PASEK)
    return ('<div style="display: flex; align-items: center; gap: 4px; '
            f'margin-left: 8px;">{pozycje}</div>')


def z_paskiem(t, aktywna):
    """Doklada powloke nawigacyjna: ksiegowanie i dziewiec pozycji w naglowku."""
    assert aktywna in ekrany.MIEJSCA, f"nieznany ekran czynny: {aktywna}"
    w_pasku = aktywna in ekrany.KLUCZE
    t = podmien(
        t, ZNAK_I_ODSTEP,
        '<span style="font-size: 15px; font-weight: 700; letter-spacing: 0.12em; '
        'text-transform: uppercase;">FINANSE</span>\n'
        f'      {_ksiegowanie(aktywna == ekrany.AKCJA.klucz)}\n'
        f'      {pasek_nawigacji(aktywna)}\n'
        '      <span style="flex: 1;"></span>\n'
        f'      {wskaznik_daty()}',
        "znak slowny, ksiegowanie, pasek i wskaznik daty w naglowku")
    t = podmien(t, STARA_W_NAGLOWKU, "", "Z-17: stara aplikacja z naglowka")
    t = podmien(t, MOTYW_W_NAGLOWKU, "", "Z-18: przelacznik motywu z naglowka")
    trafienia = [n for n in NAPISY_KSIEGOWANIA_W_STOPCE
                 if ODSYLACZ_STOPKI.format(n) in t]
    assert len(trafienia) == 1, \
        f"odsylaczy ksiegowania w stopce: {len(trafienia)}, ma byc 1"
    t = podmien(t, ODSYLACZ_STOPKI.format(trafienia[0]), "",
                "Z-17: stopka bez odsylacza")
    assert t.count('aria-current="page"') == 1, \
        f"pozycji czynnych: {t.count('aria-current=\"page\"')}, ma byc 1"
    nieczynnych = len(ekrany.PASEK) - (1 if w_pasku else 0)
    assert t.count("border-bottom: 2px solid transparent") == nieczynnych, \
        (f"pozycji nieczynnych w pasku: "
         f"{t.count('border-bottom: 2px solid transparent')}, "
         f"ma byc {nieczynnych}")
    assert "Stara aplikacja" not in t, "Z-17: odsylacz do starej aplikacji zostal"
    assert "Motyw ciemny" not in t and "Motyw jasny" not in t, \
        "Z-18: przelacznik motywu zostal w naglowku"
    assert "AI CFO" not in t, "D-47: stary znak slowny zostal w naglowku"
    return t


def ekran_jasny(nazwa_zrodla, kafel_wykresu=False, gap_34=False, wzornik=False,
                pasek=None):
    """Ekran motywu jasnego w jezyku ostatecznym: pasek -> paleta -> kafel -> faktura."""
    t = _wspolne((KAT / nazwa_zrodla).read_text(encoding="utf-8"), gap_34)
    if pasek:
        t = z_paskiem(t, pasek)
    t = przemaluj(t, MAPA_JASNA, nazwa_zrodla)
    if wzornik:
        t = _wzornik(t, "jasny")
    if kafel_wykresu:
        t = _kafel(t, KAFEL_WYKRESU)
    atramenty = {p["final"] for p in PALETA["jasny"]
                 if p["rola"].startswith(("atrament", "obrys"))}
    return nalozy_fakture(t, PAPIER_FINAL, ATRAMENT_FINAL, atramenty)


def ekran_ciemny(nazwa_zrodla, kafel_wykresu=False, gap_34=False, wzornik=False,
                 pasek=None):
    """Ekran motywu ciemnego — z TEGO SAMEGO zrodla co jasny (oba motywy roznia
    sie WYLACZNIE paleta i kaflem wykresu)."""
    t = _wspolne((KAT / nazwa_zrodla).read_text(encoding="utf-8"), gap_34)
    if pasek:
        t = z_paskiem(t, pasek)
    t = przemaluj(t, MAPA_CIEMNA, nazwa_zrodla + " (motyw ciemny)")
    if wzornik:
        t = _wzornik(t, "ciemny")
    if kafel_wykresu:
        t = _kafel(t, KAFEL_WYKRESU_CIEMNY)
    return t


# ===========================================================================
# KIERUNKI ODRZUCONE — barwy ZAMROZONE, celowo poza `paleta.json`
# ===========================================================================

ZRODLO_MAIN = (KAT / "Main-zrodlo-zamrozony.dc.html").read_text(encoding="utf-8")

#: STRAZNIK ZAMROZENIA. Odcisk zdjety z tresci zatwierdzonej w Z3 (2026-08-29):
#: znak slowny „FINANSE" (D-47) i minus typograficzny (§4.4 spec.) — obie zmiany
#: sa GLOBALNE dla produktu, wiec objely takze slad wyboru. To NIE narusza celu
#: zamrozenia (ktory dotyczy papieru i atramentu, sekcja 22–26 dokumentu decyzji
#: projektowych) — zob. komentarz przy poprzednim odcisku w historii gita.
ODCISK_ZAMROZONEGO = "e1879a6d0586fdd73af0a953da42d467fba9f7a2370abfb1eef8acb066cbe494"
_odcisk_aktualny = hashlib.sha256(ZRODLO_MAIN.encode("utf-8")).hexdigest()
assert _odcisk_aktualny == ODCISK_ZAMROZONEGO, \
    (f"zrodlo kierunkow odrzuconych zostalo zmienione bez aktualizacji odcisku "
     f"(oczekiwano {ODCISK_ZAMROZONEGO}, jest {_odcisk_aktualny})")

BAZA = podmien(
    ZRODLO_MAIN,
    'style="width: 1040px; display: flex; flex-direction: column; gap: 40px;"',
    'style="width: 1040px; display: flex; flex-direction: column; gap: 34px;"',
    "odstep miedzygrupowy 40 -> 34 px")

STARY_BLOK = ('<div style="display: flex; flex-direction: column; gap: 6px; '
              'padding-bottom: 18px;">')

KAFEL_PLASKI = "#EFE6D5"
A = podmien(
    BAZA, STARY_BLOK,
    f'<div style="display: flex; flex-direction: column; gap: 6px; '
    f'background: {KAFEL_PLASKI}; padding: 12px 20px 10px; margin: 0 -20px 8px;">',
    "kafel pod wykresem")

B = podmien(
    BAZA, STARY_BLOK,
    '<div style="display: flex; flex-direction: column; gap: 6px; padding-bottom: 13px;">',
    "blok wykresu bez kafla")
B = podmien(
    B,
    """          </div>
        </div>
        <div style="display: grid; grid-template-columns: 96px 1fr 200px 260px;""",
    """          </div>
        </div>
        <div style="height: 1px; background: #6B6252;"></div>
        <div style="height: 16px;"></div>
        <div style="display: grid; grid-template-columns: 96px 1fr 200px 260px;""",
    "linia podzialu pod wykresem")

PAPIER_ZAMROZONY = "#F3E4CD"
PALETA_PAPIER_ZAMROZONA = {
    "#F5EEE0": PAPIER_ZAMROZONY,
    "#FBF6EA": "#F8EDD9",
    "#E7DCC4": "#E2D1B3",
    "#2E2A22": "#1A160D",
    "#6B6252": "#5A5142",
    "#8C2F2A": "#791B1B",
    "#8F8268": "#786C51",
}
PALETA_GRANAT_ZAMROZONA = {
    "#1A160D": "#02143C",
    "#5A5142": "#4A5267",
    "#786C51": "#696C7A",
}
PAPIER_JASNY_ZAMROZONY = "#FBECD5"


def wariant_odrzucony(baza_html, papier, paleta_atramentu=None):
    """Odtwarza wariant z 2026-08-28 przed poludniem — poza dwiema zmianami globalnymi
    ustalonymi w Z3 (znak slowny, minus typograficzny). Nie ruszac poza tym."""
    t = baza_html
    for stara, nowa in PALETA_PAPIER_ZAMROZONA.items():
        t = re.sub(stara, nowa, t, flags=re.IGNORECASE)
    if paleta_atramentu:
        for stara, nowa in paleta_atramentu.items():
            t = podmien(t, stara, nowa, f"atrament {stara} -> {nowa}")
            t = t.replace(stara, nowa)
    if papier != PAPIER_ZAMROZONY:
        t = podmien(t, PAPIER_ZAMROZONY, papier, f"papier {PAPIER_ZAMROZONY} -> {papier}")
        t = t.replace(PAPIER_ZAMROZONY, papier)
    t = podmien(t, f"background: {KAFEL_PLASKI};", f"background: {KAFEL_WYKRESU};",
                "kafel przezroczysty")
    atrament_glowny = (paleta_atramentu or {}).get("#1A160D", "#1A160D")
    return nalozy_fakture(t, papier, atrament_glowny, set(
        (paleta_atramentu or {}).values()))


# ===========================================================================

FINAL_MAIN = ekran_jasny("Main-zrodlo.dc.html", kafel_wykresu=True, gap_34=True,
                         pasek="plynnosc")
FINAL_COMNIECZEKA = ekran_jasny("CoMnieCzeka-zrodlo.dc.html", pasek="plynnosc")
FINAL_DOBRZE = ekran_jasny("Main-Dobrze-zrodlo.dc.html", pasek="plynnosc")
FINAL_NIEWIEM = ekran_jasny("NieWiem-zrodlo.dc.html", pasek="plynnosc")
FINAL_TRZYSTANY = ekran_jasny("TrzyStany-zrodlo.dc.html", wzornik=True)

FINAL_MIESIAC = ekran_jasny("Miesiac-zrodlo.dc.html", pasek="miesiac")
FINAL_BUDZET = ekran_jasny("Budzet-zrodlo.dc.html", pasek="budzet")
FINAL_RAPORTY = ekran_jasny("Raporty-zrodlo.dc.html", pasek="raporty")
FINAL_FIRMA = ekran_jasny("Firma-zrodlo.dc.html", pasek="firma")
FINAL_MAJATEK = ekran_jasny("Majatek-zrodlo.dc.html", pasek="majatek")
FINAL_GODZINY = ekran_jasny("Godziny-zrodlo.dc.html", pasek="godziny")
FINAL_USTAWIENIA = ekran_jasny("Ustawienia-zrodlo.dc.html", pasek="ustawienia")
FINAL_DORADCA = ekran_jasny("Doradca-zrodlo.dc.html", pasek="doradca")

FINAL_KSIEGOWANIE = ekran_jasny("Ksiegowanie-zrodlo.dc.html", pasek="ksiegowanie")
FINAL_CIEMNY = ekran_ciemny("Main-zrodlo.dc.html", kafel_wykresu=True, gap_34=True,
                            pasek="plynnosc")
FINAL_TRZYSTANY_CIEMNY = ekran_ciemny("TrzyStany-zrodlo.dc.html", wzornik=True)

ZRODLA_NOWE = ("Miesiac-zrodlo.dc.html", "Budzet-zrodlo.dc.html",
               "Firma-zrodlo.dc.html", "Majatek-zrodlo.dc.html",
               "Godziny-zrodlo.dc.html", "Ustawienia-zrodlo.dc.html",
               "Doradca-zrodlo.dc.html", "Ksiegowanie-zrodlo.dc.html")
for _zrodlo in ZRODLA_NOWE:
    ekran_ciemny(_zrodlo, pasek="miesiac")

FINAL_MIESIAC_CIEMNY = ekran_ciemny("Miesiac-zrodlo.dc.html", pasek="miesiac")


def _pasek_bez_stanu(tekst):
    poczatek = tekst.index('<div style="display: flex; align-items: center; '
                           'gap: 4px; margin-left: 8px;">')
    koniec = tekst.index("</div>", tekst.index("Ustawienia</a>", poczatek))
    wycinek = tekst[poczatek:koniec]
    return (wycinek.replace(' aria-current="page"', "")
            .replace("font-weight: 600", "font-weight: 400")
            .replace("border-bottom: 2px solid " + ATRAMENT_FINAL,
                     "border-bottom: 2px solid transparent")
            .replace(ATRAMENT_FINAL, CICHY_FINAL))


CICHY_FINAL = MAPA_JASNA["#6B6252"]

ODRZ_PAPIER = wariant_odrzucony(A, PAPIER_ZAMROZONY)
ODRZ_GRANAT = wariant_odrzucony(A, PAPIER_ZAMROZONY, PALETA_GRANAT_ZAMROZONA)
ODRZ_JASNY = wariant_odrzucony(A, PAPIER_JASNY_ZAMROZONY)

assert "#02143C" in ODRZ_GRANAT and "#02143C" not in ODRZ_JASNY
assert PAPIER_JASNY_ZAMROZONY in ODRZ_JASNY and PAPIER_JASNY_ZAMROZONY not in ODRZ_GRANAT
assert "#1A160D" in ODRZ_JASNY, "wariant jasny ma trzymac atrament sepiowy"
assert PAPIER_ZAMROZONY in ODRZ_GRANAT, "wariant granatowy ma trzymac papier bez zmian"

assert PAPIER_FINAL in FINAL_MAIN and ATRAMENT_FINAL in FINAL_MAIN, \
    "wersja ostateczna ma niesc OBIE osie naraz"
assert POLE_FINAL in FINAL_MAIN, "wersja ostateczna ma niesc poprawione wypelnienie kontrolki"
assert "#F8EDD9" not in FINAL_MAIN, \
    "stare wypelnienie kontrolki zostalo — wada z Z13 nie zostala naprawiona"

Z_PASKIEM = ((FINAL_MAIN, "plynnosc"), (FINAL_COMNIECZEKA, "plynnosc"),
             (FINAL_DOBRZE, "plynnosc"), (FINAL_NIEWIEM, "plynnosc"),
             (FINAL_MIESIAC, "miesiac"), (FINAL_BUDZET, "budzet"),
             (FINAL_RAPORTY, "raporty"),
             (FINAL_FIRMA, "firma"), (FINAL_MAJATEK, "majatek"),
             (FINAL_GODZINY, "godziny"), (FINAL_USTAWIENIA, "ustawienia"),
             (FINAL_DORADCA, "doradca"), (FINAL_KSIEGOWANIE, "ksiegowanie"))
_wzorzec_paska = _pasek_bez_stanu(FINAL_MAIN)
for _tresc, _klucz in Z_PASKIEM:
    assert _pasek_bez_stanu(_tresc) == _wzorzec_paska, \
        f"pasek na ekranie {_klucz} rozni sie od wzorca"
for _e in ekrany.PASEK:
    assert f">{_e.napis}</a>" in _wzorzec_paska, \
        f"wzorzec paska nie niesie pozycji {_e.napis}"
assert _wzorzec_paska.count("<a href=") == len(ekrany.PASEK), \
    f"pozycji we wzorcu paska: {_wzorzec_paska.count('<a href=')}"

PLIKI = (
    ("Main.dc.html", FINAL_MAIN),
    ("CoMnieCzeka.dc.html", FINAL_COMNIECZEKA),
    ("Main-Dobrze.dc.html", FINAL_DOBRZE),
    ("NieWiem.dc.html", FINAL_NIEWIEM),
    ("TrzyStany.dc.html", FINAL_TRZYSTANY),
    ("Miesiac.dc.html", FINAL_MIESIAC),
    ("Budzet.dc.html", FINAL_BUDZET),
    ("Raporty.dc.html", FINAL_RAPORTY),
    ("Firma.dc.html", FINAL_FIRMA),
    ("Majatek.dc.html", FINAL_MAJATEK),
    ("Godziny.dc.html", FINAL_GODZINY),
    ("Ustawienia.dc.html", FINAL_USTAWIENIA),
    ("Doradca.dc.html", FINAL_DORADCA),
    ("Ksiegowanie.dc.html", FINAL_KSIEGOWANIE),
    ("Miesiac-Ciemny.dc.html", FINAL_MIESIAC_CIEMNY),
    ("Main-Ciemny.dc.html", FINAL_CIEMNY),
    ("TrzyStany-Ciemny.dc.html", FINAL_TRZYSTANY_CIEMNY),
    ("Main-B.dc.html", B),
    ("Main-Papier.dc.html", ODRZ_PAPIER),
    ("Main-Papier-Granat.dc.html", ODRZ_GRANAT),
    ("Main-Papier-Jasny.dc.html", ODRZ_JASNY),
)


def _kontrola_wszystkich_plikow_dc():
    """Kontrola NIE ograniczona do PLIKI generowanych przez ten skrypt.

    Znalezisko Sophii (recenzja Z3, commit 264afa0): `--kontrola` sprawdzala
    WYLACZNIE 21 plikow z krotki `PLIKI` — nie widziala `CoMamZrobic.dc.html`
    (plik rowny, ale hand-authored, poza generatorem) ani zadnego z pieciu
    plikow archiwalnych (Os/Waga/Zdanie/Main-Reka/Main-Reka-Papier). Sprawdzenie,
    do ktorego nic nie dociera, melduje sukces (CLAUDE.md §8, "kontrola licznosci
    obok mutacji"). Ta funkcja przegląda KAZDY plik `*.dc.html` w katalogu —
    liczba jest WYNIKIEM `glob`, nie stala wpisana z gory, wiec cichy ubytek
    pliku (np. skasowanie `CoMamZrobic.dc.html`) obnizy ja i będzie widoczny.
    """
    pliki = sorted(KAT.glob("*.dc.html"))
    assert (KAT / "CoMamZrobic.dc.html") in pliki, \
        "CoMamZrobic.dc.html zniknal z katalogu makiet"
    # D-55 dotyczy EKRANU ZYWEGO, nie sladu historycznego. Zrodlo zamrozone
    # (`Main-zrodlo-zamrozony.dc.html`) i jego pochodne ("kierunki odrzucone":
    # Main-B, Main-Papier*) maja odtwarzac stan SPRZED POLUDNIA 2026-08-28
    # co do bajta — a element „ile moge jeszcze rozdysponowac” byl tam
    # PRAWDZIWY w tamtej chwili; D-16 (uchylajaca D-10) zapadla dopiero
    # o 16:50, czyli PO zamrozeniu. Usuniecie go stamtad fałszowałoby historie,
    # ktora ten plik ma jedyny obowiazek wiernie pokazywac. Main-Reka* to
    # ten sam rodzaj sladu (naglowek sprzed Z-17/Z-18) — wylaczone z tego
    # samego powodu, nie przez przeoczenie.
    ARCHIWALNE_WYLACZONE_Z_D55 = {
        "Main-zrodlo-zamrozony.dc.html", "Main-B.dc.html", "Main-Papier.dc.html",
        "Main-Papier-Granat.dc.html", "Main-Papier-Jasny.dc.html",
        "Main-Reka.dc.html", "Main-Reka-Papier.dc.html",
    }
    zly_znak, zly_element = [], []
    for plik in pliki:
        tresc = plik.read_text(encoding="utf-8")
        if "AI CFO" in tresc:
            zly_znak.append(plik.name)
        if (plik.name.startswith("Main") and "rozdysponow" in tresc.lower()
                and plik.name not in ARCHIWALNE_WYLACZONE_Z_D55):
            zly_element.append(plik.name)
    print(f"\nKontrola WSZYSTKICH plikow .dc.html w katalogu: {len(pliki)} sprawdzonych.")
    for n in zly_znak:
        print(f"  ZOSTAL STARY ZNAK SLOWNY „AI CFO”: {n}")
    for n in zly_element:
        print(f"  WROCIL ELEMENT „rozdysponowac” (D-55, ma byc na Budzecie, nie na Main*): {n}")
    return len(pliki), len(zly_znak) + len(zly_element)


if __name__ == "__main__":
    if "--kontrola" in sys.argv:
        rozne = 0
        for nazwa, tresc in PLIKI:
            plik = KAT / nazwa
            zgodne = plik.exists() and plik.read_text(encoding="utf-8") == tresc
            rozne += 0 if zgodne else 1
            print(f"{nazwa:32s} {'zgodny z repo' if zgodne else 'ROZNI SIE OD REPO'}")
        ile_sprawdzonych, rozne_wszystkie = _kontrola_wszystkich_plikow_dc()
        rozne += rozne_wszystkie
        print(f"\nPLIKOW .DC.HTML SPRAWDZONYCH LACZNIE: {ile_sprawdzonych}")
        print(f"ROZBIEZNOSCI: {rozne}")
        sys.exit(1 if rozne else 0)
    for nazwa, tresc in PLIKI:
        (KAT / nazwa).write_text(tresc, encoding="utf-8")
        print(f"{nazwa:32s} {len(tresc)} znakow")
