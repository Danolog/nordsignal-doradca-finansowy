# -*- coding: utf-8 -*-
"""STRAZNIK OBIETNICY PASKA (W7).

Pasek renderuje `href={`/${klucz}`}` dla kazdej pozycji mapy ekranow, a
zbudowane sa dwa ekrany z jedenastu. Przed W7 znaczylo to, ze DZIEWIEC
Z DZIEWIECIU odsylaczy paska konczylo sie strona wbudowana w Next —
po angielsku, bez zdania o tym, co sie stalo (pomiar `curl`, 2026-08-29:
caly widoczny tekst `/miesiac` to »404: This page could not be found.«).
To lamie CLAUDE.md §3.7: awaria do stanu uzytecznego, nie do zera.

CO PILNUJE TEN PLIK, A CZEGO NIE. Tutaj stoi to, co widac w ZRODLE:
ze kazdy klucz ma gdzie prowadzic, ze lista ekranow nie urodzila sie
w drugim miejscu i ze strona nieznanego adresu mowi po polsku. Tego,
co uzytkownik NAPRAWDE zobaczy pod tymi adresami, ten plik nie widzi —
mierzy to przejsciem `interfejs/narzedzia/straznik-odsylacze-paska.mjs`.
Rozdzial jest celowy: test statyczny nie wymaga uruchomionej aplikacji,
wiec stoi w suicie; przejscie wymaga przegladarki, wiec stoi obok.

KONTROLA LICZNOSCI W KAZDYM TESCIE. Sprawdzenie, do ktorego nic nie
dociera, melduje sukces — petla po pustej liscie kluczy przeszlaby
»zero blednych odsylaczy« tak samo jak petla po komplecie.
"""
import pathlib
import re

KATALOG = pathlib.Path(__file__).resolve().parent.parent
APLIKACJA = KATALOG / "interfejs" / "app"
MAPA_TS = KATALOG / "interfejs" / "lib" / "ekrany.ts"
TRASA_BEZ_EKRANU = APLIKACJA / "[ekran]" / "page.tsx"
NIEZNANY_ADRES = APLIKACJA / "not-found.tsx"
KORZEN = APLIKACJA / "page.tsx"
POWLOKA = APLIKACJA / "powloka.tsx"


def _klucze_paska() -> list[str]:
    tekst = MAPA_TS.read_text(encoding="utf-8")
    blok = tekst[tekst.index("export const PASEK"):tekst.index("] as const;")]
    return re.findall(r'klucz:\s*"([^"]+)"', blok)


def test_kazdy_klucz_paska_MA_GDZIE_prowadzic():
    """Odsylacz paska konczy sie ALBO zbudowanym ekranem, ALBO trasa, ktora
    mowi po polsku, ze tej czesci jeszcze nie ma. Nigdy strona Next."""
    klucze = _klucze_paska()
    assert len(klucze) == 9, f"pasek ma miec dziewiec pozycji, mapa daje {len(klucze)}"

    sprawdzonych = 0
    bez_ujscia = []
    for klucz in klucze:
        wlasny_ekran = (APLIKACJA / klucz / "page.tsx").exists()
        if not (wlasny_ekran or TRASA_BEZ_EKRANU.exists()):
            bez_ujscia.append(klucz)
        sprawdzonych += 1

    assert sprawdzonych == len(klucze), \
        f"petla obejrzala {sprawdzonych} kluczy z {len(klucze)}"
    assert bez_ujscia == [], (
        f"odsylacze paska bez ujscia: {bez_ujscia}. Kazdy z nich odda strone "
        "wbudowana w Next, po angielsku i bez zdania o tym, co zrobic (§3.7)."
    )


def test_ekran_plynnosci_STOI_POD_swoim_kluczem():
    """Pasek prowadzi na `/plynnosc`. Do W7 ekran stal pod `/`, wiec odsylacz
    do ekranu widocznego na wierzchu takze konczyl sie 404."""
    klucz = _klucze_paska()[0]
    assert klucz == "plynnosc", f"pierwsza pozycja paska to {klucz}, nie plynnosc"
    assert (APLIKACJA / klucz / "page.tsx").exists(), \
        "ekran Plynnosci nie stoi pod swoim kluczem — odsylacz paska prowadzi donikad"

    korzen = KORZEN.read_text(encoding="utf-8")
    assert "redirect(" in korzen, \
        "korzen aplikacji ma przekierowywac na ekran startowy, a nie renderowac go po raz drugi"
    assert "searchParams" in korzen, (
        "przekierowanie ma przepuszczac parametry adresu — `dzis` istnieje DLA "
        "POMIARU ODBIORCZEGO (api/wspolne.py::dzien), a bramka odwzorowania go uzywa"
    )


def test_trasa_bez_ekranu_NIE_MA_wpisanej_listy_ekranow():
    """Lista ekranow ma jeden nosnik po stronie interfejsu (`lib/ekrany.ts`).
    Nazwy wpisane w trasie zastepczej byly by DRUGIM NOSNIKIEM mapy — i to
    takim, ktorego straznik `test_mapa_ekranow_NIE_ROZJECHALA_sie_miedzy_
    jezykami` nie widzi, bo porownuje `ekrany.py` z `ekrany.ts`, a nie z
    ekranami (CLAUDE.md §3.2)."""
    assert TRASA_BEZ_EKRANU.exists(), f"brak trasy zastepczej: {TRASA_BEZ_EKRANU}"
    kod = TRASA_BEZ_EKRANU.read_text(encoding="utf-8")
    # Komentarz nagłówka wolno cytować klucze — pilnujemy KODU.
    kod_bez_komentarzy = re.sub(r"//[^\n]*", "", kod)

    klucze = _klucze_paska()
    wpisane = [k for k in klucze if f'"{k}"' in kod_bez_komentarzy or f"'{k}'" in kod_bez_komentarzy]
    assert len(klucze) == 9, f"kontrola licznosci: obejrzalem {len(klucze)} kluczy, nie dziewiec"
    assert wpisane == [], (
        f"klucze ekranow wpisane w trasie zastepczej: {wpisane}. Maja przychodzic "
        "z `lib/ekrany.ts`, inaczej rozjada sie z paskiem po pierwszej zmianie nazwy."
    )
    assert "@/lib/ekrany" in kod, "trasa zastepcza ma czytac mape ekranow, a nie wlasna liste"


def test_nieznany_adres_MOWI_PO_POLSKU_co_sie_stalo():
    """§3.7: aplikacja mowi, czego brakuje i co zrobic. Angielskie „404: This
    page could not be found." nie mowi ani jednego, ani drugiego — a Darek
    nie jest deweloperem (CLAUDE.md §4)."""
    assert NIEZNANY_ADRES.exists(), f"brak strony nieznanego adresu: {NIEZNANY_ADRES}"
    kod = NIEZNANY_ADRES.read_text(encoding="utf-8")
    assert "Powloka" in kod or "BezEkranu" in kod, (
        "strona nieznanego adresu ma niesc powloke — bez paska uzytkownik wychodzi "
        "z niej przyciskiem »wstecz«, a nie jednym klikiem"
    )
    # Zdania mieszkaja w `lib/napisy.ts` — tutaj ma byc WOLANIE, nie tekst.
    assert "@/lib/napisy" in kod, \
        "brzmienia maja przychodzic z `lib/napisy.ts`, jedynego nosnika napisow"

    napisy = (KATALOG / "interfejs" / "lib" / "napisy.ts").read_text(encoding="utf-8")
    for nazwa in ("NAPISY_NIEZNANEGO_ADRESU", "NAPISY_NIEZBUDOWANEGO"):
        assert f"export const {nazwa}" in napisy, f"brak brzmien {nazwa}"


def test_zaden_odsylacz_naglowka_NIE_JEST_wpisany_recznie():
    """Adres odsylacza powstaje z klucza mapy. Adres wpisany w powloce byłby
    drugim nosnikiem miejsca, w ktorym stoi ekran — i milczalby, gdy ekran
    sie przeprowadzi."""
    kod = re.sub(r"//[^\n]*", "", POWLOKA.read_text(encoding="utf-8"))
    wpisane = re.findall(r'href="(/[^"{]*)"', kod)
    assert wpisane == [], f"adresy wpisane recznie w powloce: {wpisane}"
    # Kontrola licznosci: powloka MA renderowac odsylacze — plik bez ani
    # jednego `href` przeszedlby asercje wyzej nic nie udowodniwszy.
    wszystkie = re.findall(r"href=", kod)
    assert len(wszystkie) == 2, (
        f"powloka renderuje {len(wszystkie)} odsylaczy w nagłowku, spodziewam sie dwoch "
        "(pasek w petli + akcja przy znaku slownym)"
    )
