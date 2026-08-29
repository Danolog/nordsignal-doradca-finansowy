# -*- coding: utf-8 -*-
"""Pomiar SZEROKOSCI NAPISU w makiecie — narzedzie do makiet, nie do produkcji.

DLACZEGO POWSTAL. Pasek nawigacji (M2) musi pomiescic osiem pozycji obok
znaku slownego, przycisku ksiegowania i dwoch kontrolek uzytkowych, przy
szerokosci ramki 1440 px. Zdanie „wydaje sie, ze sie miesci" nie jest
dowodem (CLAUDE.md par. 8, regula v1.16) — potrzebna jest liczba i prog.
`kontrast.py` mierzy barwe; ten plik mierzy szerokosc. Rozdzielone, bo to
dwie rozne osie i dwa rozne progi.

JAK MIERZY. Przez warstwe tekstu systemu macOS (pyobjc), czyli tym samym
silnikiem, ktory rysuje napisy na ekranie. Nie jest to oszacowanie z tabeli
szerokosci znakow — to zapytanie o realny naddatek (ang. advance width)
konkretnego kroju w konkretnym stopniu, razem ze swiatlem miedzyliterowym.

GRANICE TEGO NARZEDZIA, nazwane wprost:
  1. Mierzy CZTERY kroje ze stosu makiety, ktore sa na tej maszynie:
     systemowy (`-apple-system`, czyli SF Pro), Helvetica Neue, Arial
     i Helvetica. Werdykt stoi na WARTOSCI NAJWIEKSZEJ ze wszystkich,
     czyli na przypadku najgorszym z tych, ktore umiem zmierzyc.
     `Segoe UI` (Windows) na tej maszynie nie wystepuje i NIE ZOSTAL
     zmierzony — to nazwana luka dowodowa, nie zalozenie, ze jest wezszy.
  2. Nie widzi zawijania, nie widzi `flex-shrink`, nie widzi zaokraglen
     podpikselowych przegladarki. Odpowiada na jedno pytanie: ile pikseli
     zajmie ten napis w tej linii.
  3. `letter-spacing` w CSS dokłada światło ZA kazda litera, takze za
     ostatnia; `NSKernAttributeName` robi to samo. Roznica wobec przegladarki
     nie przekracza wiec jednego kroku swiatla.

URUCHOMIENIE (z katalogu, w ktorym lezy ten plik):
    python3 miara.py            # pomiar paska nawigacji, z werdyktem
"""
import sys

try:
    from AppKit import (NSAttributedString, NSFont, NSFontAttributeName,
                        NSKernAttributeName)
except ImportError:  # pragma: no cover — narzedzie warsztatowe
    print("Brak pyobjc — pomiar szerokosci niewykonalny na tej maszynie.")
    sys.exit(2)

#: Szerokosc ramki i wciecie boczne naglowka — wprost z `Main-zrodlo.dc.html`
#: (`padding: 14px 40px`). Zmiana ktoregokolwiek unieważnia pomiar.
RAMKA = 1440
WCIECIE = 40
DOSTEPNE = RAMKA - 2 * WCIECIE


#: Kroje ze stosu makiety, ktore da sie zmierzyc na tej maszynie. Werdykt
#: stoi na WARTOSCI WIEKSZEJ ze wszystkich — czyli na przypadku gorszym
#: z tych, ktore umiem sprawdzic. Krojow nieobecnych w systemie funkcja nie
#: zglasza jako zera; pomija je, a `--kroje` wypisuje, ktore wzieto pod uwage.
KROJE = {
    "systemowy": None,
    "HelveticaNeue": ("HelveticaNeue-Bold", "HelveticaNeue"),
    "Arial": ("Arial-BoldMT", "ArialMT"),
    "Helvetica": ("Helvetica-Bold", "Helvetica"),
}


def szerokosc(tekst, stopien, *, swiatlo=0.0, waga="zwykla",
              wielkie=False):
    """Szerokosc napisu w pikselach — najwieksza ze zmierzonych krojow.

    `swiatlo` podaje sie w jednostce `em` (tak jak `letter-spacing` w CSS);
    przeliczenie na piksele robi ta funkcja, zeby wolajacy nie powtarzal
    mnozenia przy kazdym napisie.
    """
    if wielkie:
        tekst = tekst.upper()
    kern = stopien * swiatlo
    wyniki = []
    for nazwa in KROJE:
        if nazwa == "systemowy":
            font = (NSFont.boldSystemFontOfSize_(stopien) if waga == "gruba"
                    else NSFont.systemFontOfSize_(stopien))
        else:
            gruby, zwykly = KROJE[nazwa]
            font = NSFont.fontWithName_size_(
                gruby if waga == "gruba" else zwykly, stopien)
        if font is None:
            continue
        atrybuty = {NSFontAttributeName: font}
        if kern:
            atrybuty[NSKernAttributeName] = kern
        napis = NSAttributedString.alloc().initWithString_attributes_(
            tekst, atrybuty)
        wyniki.append(float(napis.size().width))
    return max(wyniki)


# --- pasek nawigacji ------------------------------------------------------

#: Osiem miejsc paska (M1) — WOLANE z `ekrany.py`, nie przepisane. Napis
#: w pasku jest RZECZOWNIKIEM tematu ekranu, nie nazwa zakladki starej
#: aplikacji (dokument, sekcja 28.2).
import ekrany  # noqa: E402

POZYCJE = ekrany.NAPISY
KSIEGOWANIE = ekrany.AKCJA.napis

#: Warianty nazw sprawdzane obok wybranych — pomiar ma pokazac, ile kosztuje
#: dluzsza nazwa, a nie tylko czy wybrana sie miesci.
WARIANTY = {"Godziny": "Rejestr godzin", "Firma": "JDG i podatki",
            "Płynność": "Księga płynności"}

STOPIEN_POZYCJI = 13
SWIATLO_POZYCJI = 0.12          # jak naglowki kolumn w `Main.dc.html`
WYPELNIENIE_POZYCJI = 2 * 12    # padding: 0 12px
ODSTEP_POZYCJI = 4              # gap miedzy pozycjami paska

#: Elementy linii pierwszej naglowka — te, ktore juz sa w `Main.dc.html`,
#: plus przycisk ksiegowania przeniesiony ze stopki (P-3).
#: Zmieniony w Z3 (2026-08-29, D-47 + regula minus-zapasu): „FINANSE",
#: swiatlo 0,12 em (jak pozycje paska), a nie 0,16 em jak przy „AI CFO" —
#: patrz `buduj-makiety.py`, komentarz przy `ZNAK_I_ODSTEP`.
ZNAK_SLOWNY = ("FINANSE", 15, 0.12, "gruba", True)
IKONA_KSIEGOWANIA = 16 + 8      # znak plus (16 px) + odstep do napisu
#: PO Z-17 I Z-18 LINIA NAGLOWKA NIE MA JUZ ZADNEJ KONTROLKI UZYTKOWEJ.
#: „Stara aplikacja" zeszla najpierw do stopki (28.4), a potem znikla
#: calkowicie (Z-17) — nie przechodzimy juz do wygaszanego programu.
#: Przelacznik motywu przeniosl sie do Ustawien (Z-18). Pusta krotka jest tu
#: WYPOWIEDZIA, nie brakiem: gdyby ktos dolozyl kontrolke do naglowka, ma
#: dopisac ja tutaj i zobaczyc, ile kosztuje.
UZYTKOWE = ()
WYPELNIENIE_KONTROLKI = 2 * 16  # padding: 0 16px, jak w `Main.dc.html`
ODSTEP_LINII = 16               # gap w linii naglowka

#: NAPRAWA (2026-08-29, recenzja Sophii, commit 264afa0). Do tej pory ten plik
#: NIE liczyl wskaznika daty (Z-29, `buduj-makiety.py::wskaznik_daty`) w ogole —
#: powstal PRZED nim i nikt go tu nie dopisal. Skutek: „obie w jednej linii”
#: drukowalo zapas 213,8 px (potem 200,6 po zmianie znaku), a realny zapas po
#: doliczeniu wskaznika to ok. 45 px — narzedzie mierzylo wlasna, niepelna
#: definicje wiersza, nie prawdziwy uklad. Wskaznik NIE jest „kontrolka
#: uzytkowa” (`UZYTKOWE`) — jest zwyklym tekstem — dlatego dostaje wlasna
#: stala, a nie wchodzi do tamtej krotki.
WSKAZNIK_DATY_PRZYKLAD = "6 października 2026 · 09:40"
#: Pasek nawigacji niesie WLASNY `margin-left: 8px` (`buduj-makiety.py::
#: pasek_nawigacji`), NIEZALEZNY od `gap: 16px` rodzica — obie wartosci licza
#: sie osobno, sumuja.
MARGIN_PASEK = 8
#: Piec dzieci w wierszu naglowka (znak, ksiegowanie, pasek, dystans, wskaznik)
#: daje CZTERY odstepy `gap: 16px` rodzica — flex `gap` dziala MIEDZY kazda
#: para dzieci, WLACZNIE z tymi po obu stronach elementu `flex: 1`, ktory sam
#: nie zajmuje miejsca, ale odstepow wokol siebie nie kasuje.
LICZBA_DZIECI_NAGLOWKA = 5


def _pozycja(napis):
    return szerokosc(napis, STOPIEN_POZYCJI, swiatlo=SWIATLO_POZYCJI,
                     wielkie=True) + WYPELNIENIE_POZYCJI


def pasek():
    """Suma szerokosci osmiu pozycji paska razem z odstepami."""
    razem = sum(_pozycja(n) for n in POZYCJE)
    razem += ODSTEP_POZYCJI * (len(POZYCJE) - 1)
    return razem


def linia_pierwsza():
    """Suma szerokosci linii ze znakiem slownym, ksiegowaniem i kontrolkami."""
    tekst, stopien, swiatlo, waga, wielkie = ZNAK_SLOWNY
    razem = szerokosc(tekst, stopien, swiatlo=swiatlo, waga=waga,
                      wielkie=wielkie)
    razem += (szerokosc(KSIEGOWANIE, 15) + WYPELNIENIE_KONTROLKI
              + IKONA_KSIEGOWANIA)
    for napis in UZYTKOWE:
        razem += szerokosc(napis, 15) + WYPELNIENIE_KONTROLKI
    razem += ODSTEP_LINII * (2 + len(UZYTKOWE))
    return razem


def wiersz_naglowka(znak_slowny=ZNAK_SLOWNY):
    """Cala szerokosc wiersza naglowka NAPRAWDE, wliczajac wskaznik daty.

    Zastepuje dawne `pasek() + linia_pierwsza() + ODSTEP_LINII`, ktore
    pomijaly wskaznik i liczyly jeden odstep zamiast czterech + marginesu
    paska. Rozklad zgodny z `buduj-makiety.py::z_paskiem`:
      [znak] [ksiegowanie] [pasek margin-left:8] [dystans flex:1] [wskaznik]
    """
    tekst, stopien, swiatlo, waga, wielkie = znak_slowny
    znak_w = szerokosc(tekst, stopien, swiatlo=swiatlo, waga=waga, wielkie=wielkie)
    ksiegowanie_w = szerokosc(KSIEGOWANIE, 15) + WYPELNIENIE_KONTROLKI + IKONA_KSIEGOWANIA
    pasek_w = pasek()
    wskaznik_w = szerokosc(WSKAZNIK_DATY_PRZYKLAD, 13)
    gapy = ODSTEP_LINII * (LICZBA_DZIECI_NAGLOWKA - 1)
    return znak_w + ksiegowanie_w + pasek_w + wskaznik_w + gapy + MARGIN_PASEK


def _werdykt(ile, prog):
    return "MIESCI SIE" if ile <= prog else "NIE MIESCI SIE"


if __name__ == "__main__":
    print(f"Ramka {RAMKA} px, wciecie {WCIECIE} px -> dostepne {DOSTEPNE} px\n")

    print("POZYCJE PASKA (13 px, swiatlo 0,12 em, wersaliki, wypelnienie 24 px)")
    for napis in POZYCJE:
        wiersz = f"  {napis:12s} {_pozycja(napis):7.1f} px"
        if napis in WARIANTY:
            inny = WARIANTY[napis]
            wiersz += (f"   (wariant „{inny}”: {_pozycja(inny):.1f} px, "
                       f"+{_pozycja(inny) - _pozycja(napis):.1f})")
        print(wiersz)

    p, l = pasek(), linia_pierwsza()
    print(f"\n  pasek dziewieciu pozycji razem  {p:7.1f} px")
    print(f"  linia znak+ksiegowanie+2        {l:7.1f} px  (BEZ wskaznika daty — "
          f"patrz niżej)")

    print("\n  CALY WIERSZ NAGLOWKA, naprawione (ze wskaznikiem daty, marginesem")
    print("  paska i CZTEREMA odstepami — nie jednym):")
    for opis, znak in (("„FINANSE” (obowiazujacy, D-47/D-57)", ZNAK_SLOWNY),
                       ("„Doradca Finansowy” (odrzucony w Z3)",
                        ("Doradca Finansowy", 15, 0.12, "gruba", True))):
        w = wiersz_naglowka(znak)
        print(f"    {opis:42s} {w:7.1f} px  prog {DOSTEPNE} px  "
              f"{_werdykt(w, DOSTEPNE)}  (zapas {DOSTEPNE - w:+.1f} px)")

    # WARIANT ODRZUCONY, ZMIERZONY: ksiegowanie jako DZIEWIATA POZYCJA paska,
    # bez kontrolki o obrysie. Mierzymy go, zeby rozstrzygniecie „zostaje
    # osobno" stalo na liczbie, a nie na przekonaniu — i zeby bylo widac, ze
    # liczba tego sporu NIE rozstrzyga: oba warianty mieszcza sie z zapasem
    # wiekszym niz 300 px, wiec decyduje znaczenie, nie miejsce (sekcja 41.3).
    znak = szerokosc(ZNAK_SLOWNY[0], ZNAK_SLOWNY[1], swiatlo=ZNAK_SLOWNY[2],
                     waga=ZNAK_SLOWNY[3], wielkie=ZNAK_SLOWNY[4])
    dziewiata = _pozycja(KSIEGOWANIE)
    pasek_rozszerzony = p + ODSTEP_POZYCJI + dziewiata
    wskaznik_w = szerokosc(WSKAZNIK_DATY_PRZYKLAD, 13)
    # 4 dzieci w tym ukladzie (znak, pasek rozszerzony, dystans, wskaznik) -> 3 odstepy.
    razem9 = znak + pasek_rozszerzony + wskaznik_w + ODSTEP_LINII * 3 + MARGIN_PASEK
    print("\n  WARIANT ODRZUCONY — ksiegowanie jako 10. pozycja paska (ze wskaznikiem daty)")
    print(f"  pozycja ksiegowania w pasku {dziewiata:7.1f} px")
    print(f"  znak + dziesiec pozycji + wskaznik  {razem9:7.1f} px "
          f"prog {DOSTEPNE} px  {_werdykt(razem9, DOSTEPNE)}")
    print(f"  ZAPAS wariantu odrzuconego          {DOSTEPNE - razem9:7.1f} px")

    # Prog konsolidacji, jawnie: zapas mniejszy niz najwezsza pozycja paska
    # znaczy, ze KAZDA zmiana nazwy wymaga ponownego pomiaru. Liczony wobec
    # PRAWDZIWEGO wiersza (`wiersz_naglowka`), nie wobec niepelnej sumy sprzed
    # naprawy.
    najwezsza = min(_pozycja(n) for n in POZYCJE)
    zapas = DOSTEPNE - wiersz_naglowka()
    print(f"  najwezsza pozycja paska     {najwezsza:7.1f} px  -> zapas prawdziwego "
          f"wiersza ({zapas:.1f} px) jest "
          f"{'MNIEJSZY' if zapas < najwezsza else 'wiekszy'} niz jedna pozycja paska")

    # Kontrola narzedzia na wartosci znanej: napis pusty ma miec zero, a napis
    # dwa razy dluzszy ma byc szerszy. Bez tego nie wiadomo, czy funkcja
    # w ogole cokolwiek liczy — pulapka nr 4 z przekazania (narzedzie mierzace
    # wlasna podloge).
    assert szerokosc("", 13) == 0.0, "kontrola: pusty napis ma miec zero"
    assert szerokosc("MM", 13) > szerokosc("M", 13), \
        "kontrola: dluzszy napis ma byc szerszy"
    print("\nKontrola narzedzia na wartosci znanej: przeszla.")

    obecne = [n for n in KROJE if n == "systemowy"
              or NSFont.fontWithName_size_(KROJE[n][1], 13) is not None]
    print(f"Kroje wziete pod uwage: {', '.join(obecne)}")
    print("Krój `Segoe UI` nie wystepuje na tej maszynie — niezmierzony.")
