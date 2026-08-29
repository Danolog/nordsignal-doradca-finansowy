"""Pomiar stosunku kontrastu wg WCAG 2.2 — narzedzie do makiet, nie do produkcji.

DLACZEGO OSOBNY PLIK, A NIE OCENA W DOKUMENCIE. Fundament §6A wymaga liczby
i progu, nie zdania „kontrast jest dobry". Zdanie „zmierzylam" bez wyjscia
komendy nie jest dowodem (CLAUDE.md §8, regula v1.16).

WZOR. Luminancja wzgledna i stosunek kontrastu wprost z WCAG 2.2:
  skladowa s w [0,1]:  s <= 0.04045 ? s/12.92 : ((s+0.055)/1.055)^2.4
  L = 0.2126*R + 0.7152*G + 0.0722*B
  stosunek = (Ljasniejsza + 0.05) / (Lciemniejsza + 0.05)

GRANICA TEGO NARZEDZIA, nazwana wprost: liczy WYLACZNIE pary barw plaskich.
Nie widzi przezroczystosci (`opacity`), nie widzi tekstu na gradiencie ani
na fakturze papieru zlozonej z dwoch warstw. Gdzie makieta uzywa warstwy
polprzezroczystej, do pomiaru podaje sie barwe ZLOZONA — funkcja `zloz`.
Fakture zlozona z wielu warstw sklada `skrajne_faktury` — i podaje jej punkt
NAJCIEMNIEJSZY i NAJJASNIEJSZY, bo srednia faktury nie mowi nic o tym, gdzie
napis przestaje byc czytelny.

CZTERY DOLOZONE POMIARY (2026-08-28, zlecenie Z2c/Z4), kazdy z powodem:

1. `szarosc` — filtr skali szarosci wymagany wprost przez fundament §6A
   („kolor jako jedyny nosnik informacji"). Zachowuje luminancje wzgledna
   WCAG, wiec odpowiada na pytanie „czy po odjeciu barwy cokolwiek zostaje",
   a nie na pytanie „jak to wyglada w czarno-bialej gazecie".

2. `symuluj` — symulacja widzenia bez jednego z czopkow. Deuteranopia
   i protanopia to najczestsza para nierozroznialna: czerwien i zielen.
   Macierze: Machado, Oliveira, Fernandes 2009, „A Physiologically-based Model
   for Simulation of Color Vision Deficiency", IEEE TVCG 15(6), tabela dla
   stopnia 1,0; stosowane w RGB LINIOWYM, nie w sRGB.
   TO JEST MODEL, NIE POMIAR NA CZLOWIEKU — i tak go opisuje.

3. `lab` / `chroma` / `roznica_lab` — CIELAB (D65, obserwator 2°). Potrzebne,
   bo stosunek kontrastu widzi WYLACZNIE jasnosc: dwie barwy o tej samej
   luminancji i przeciwnym odcieniu daja 1,00:1 i wygladaja jak brak roznicy,
   choc oko widzi je jako dwie rozne rzeczy. Bez chromy nie da sie uczciwie
   powiedziec „ta para rozni sie barwa, a nie jasnoscia".

4. `skrajne_faktury` — patrz wyzej.
"""

import sys


def _kanaly(hex_barwy: str) -> tuple[float, float, float]:
    s = hex_barwy.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(z * 2 for z in s)
    if len(s) != 6:
        raise ValueError(f"Barwa {hex_barwy!r} nie jest zapisem szesnastkowym RRGGBB.")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _liniowa(s: float) -> float:
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def luminancja(hex_barwy: str) -> float:
    r, g, b = (_liniowa(k) for k in _kanaly(hex_barwy))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def stosunek(a: str, b: str) -> float:
    la, lb = luminancja(a), luminancja(b)
    jasniejsza, ciemniejsza = max(la, lb), min(la, lb)
    return (jasniejsza + 0.05) / (ciemniejsza + 0.05)


def zloz(wierzch: str, spod: str, krycie: float) -> str:
    """Barwa wypadkowa warstwy `wierzch` o kryciu `krycie` na tle `spod`.

    Potrzebne, bo `opacity` w CSS nie zmienia barwy zapisanej w stylu, a mozg
    i tak widzi wypadkowa. Bez tego pomiar klamalby na korzysc makiety.
    """
    w, s = _kanaly(wierzch), _kanaly(spod)
    mieszane = tuple(w[i] * krycie + s[i] * (1 - krycie) for i in range(3))
    return "#" + "".join(f"{round(k * 255):02X}" for k in mieszane)


def _werdykt(wynik: float, prog: float) -> str:
    return "PRZECHODZI" if wynik + 1e-9 >= prog else "NIE PRZECHODZI"


def zmierz(pary) -> int:
    """`pary`: (opis, barwa, tlo, prog). Zwraca liczbe par, ktore nie przeszly."""
    upadki = 0
    szerokosc = max(len(p[0]) for p in pary)
    for opis, barwa, tlo, prog in pary:
        wynik = stosunek(barwa, tlo)
        stan = _werdykt(wynik, prog)
        if stan == "NIE PRZECHODZI":
            upadki += 1
        print(f"{opis.ljust(szerokosc)}  {barwa} na {tlo}  "
              f"{wynik:5.2f}:1  prog {prog}:1  {stan}")
    print(f"\nZMIERZONO PAR: {len(pary)}   NIE PRZESZLO: {upadki}")
    return upadki



# ---------------------------------------------------------------------------
# Skala szarosci — fundament §6A, „kolor jako jedyny nosnik informacji"
# ---------------------------------------------------------------------------

def szarosc(hex_barwy: str) -> str:
    """Barwa po filtrze skali szarosci ZACHOWUJACYM luminancje wzgledna WCAG.

    Wybor filtra jest decyzja, nie szczegolem. Filtr „srednia skladowych"
    i filtr „luma ITU-R BT.601" daja inne szarosci, a §6A pyta o to, czy
    informacja przezyje odjecie barwy — czyli o luminancje, ta sama wielkosc,
    ktora stoi we wzorze kontrastu. Dzieki temu kontrast pary PO odbarwieniu
    jest dokladnie taki sam jak przed nim, a caly ubytek widac w chromie.
    """
    l = luminancja(hex_barwy)
    s = 12.92 * l if l <= 0.0031308 else 1.055 * (l ** (1 / 2.4)) - 0.055
    k = round(max(0.0, min(1.0, s)) * 255)
    return "#" + f"{k:02X}" * 3


# ---------------------------------------------------------------------------
# Widzenie barw bez jednego czopka — Machado i in. 2009, stopien 1,0
# ---------------------------------------------------------------------------

#: Macierze stosowane w RGB LINIOWYM. Zrodlo w docstringu modulu.
MACIERZE = {
    "deuteranopia": ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501, 0.047413),
                     (-0.011820, 0.042940, 0.968881)),
    "protanopia": ((0.152286, 1.052583, -0.204868),
                   (0.114503, 0.786281, 0.099216),
                   (-0.003882, -0.048116, 1.051998)),
}


def _do_sRGB(s: float) -> float:
    return 12.92 * s if s <= 0.0031308 else 1.055 * (s ** (1 / 2.4)) - 0.055


def symuluj(hex_barwy: str, rodzaj: str = "deuteranopia") -> str:
    """Jak ta barwa wyglada dla osoby bez czopka L (protanopia) lub M (deuteranopia).

    MODEL, NIE POMIAR. Sluzy do jednego pytania: czy para czerwien/zielen,
    ktora dla mnie jest para przeciwienstw, dla czesci odbiorcow zlewa sie
    w jedna barwe. Odpowiedz „zlewa sie" NIE jest wyrokiem na projekt —
    jest wymogiem, zeby informacje niosl takze drugi nosnik (§6A).
    """
    m = MACIERZE[rodzaj]
    r, g, b = (_liniowa(k) for k in _kanaly(hex_barwy))
    wynik = []
    for w in m:
        k = w[0] * r + w[1] * g + w[2] * b
        wynik.append(round(max(0.0, min(1.0, _do_sRGB(max(0.0, min(1.0, k))))) * 255))
    return "#" + "".join(f"{k:02X}" for k in wynik)


# ---------------------------------------------------------------------------
# CIELAB — bo stosunek kontrastu nie widzi barwy, tylko jasnosc
# ---------------------------------------------------------------------------

#: Bialy punkt D65, obserwator 2°.
BIALY_D65 = (0.95047, 1.00000, 1.08883)


def lab(hex_barwy: str) -> tuple[float, float, float]:
    """(L*, a*, b*) w CIELAB, D65."""
    r, g, b = (_liniowa(k) for k in _kanaly(hex_barwy))
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = (f(k / w) for k, w in zip((x, y, z), BIALY_D65))
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def chroma(hex_barwy: str) -> float:
    """C* — ile w barwie jest barwy. 0 = szarosc neutralna."""
    _, a, b = lab(hex_barwy)
    return (a * a + b * b) ** 0.5


def roznica_lab(a: str, b: str) -> float:
    """Roznica dostrzegalna ΔE*ab. ~2,3 to prog ledwie zauwazalny (JND)."""
    la, lb = lab(a), lab(b)
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


# ---------------------------------------------------------------------------
# Faktura papieru — pomiar na skrajnosciach, nie na sredniej
# ---------------------------------------------------------------------------

def skrajne_faktury(baza: str, warstwy) -> tuple[str, str]:
    """Najciemniejszy i najjasniejszy punkt faktury zlozonej z warstw.

    `warstwy`: ciag par (barwa, krycie). Kazda warstwa albo w danym punkcie
    lezy w pelnym kryciu, albo jej tam nie ma — wiec skrajnosci to zlozenie
    WSZYSTKICH warstw ciemniejszych od bazy (punkt najciemniejszy) i wszystkich
    jasniejszych (punkt najjasniejszy).

    DLACZEGO NIE SREDNIA. Faktura o sredniej rownej bazie nie zmienia nic
    w pomiarze sredniej, a potrafi zjesc caly zapas kontrastu w miejscu,
    w ktorym akurat stoi kreska cyfry. Pomiar sredniej meldowalby sukces.
    """
    ciemny, jasny = baza, baza
    for barwa, krycie in warstwy:
        zlozony = zloz(barwa, ciemny, krycie)
        if luminancja(zlozony) < luminancja(ciemny):
            ciemny = zlozony
    for barwa, krycie in warstwy:
        zlozony = zloz(barwa, jasny, krycie)
        if luminancja(zlozony) > luminancja(jasny):
            jasny = zlozony
    return ciemny, jasny

def odcien(hex_barwy: str) -> float:
    """Kat odcienia h* w stopniach (CIELCh). Potrzebny, zeby powiedziec
    „ta barwa zostala w rodzinie", zamiast to zalozyc."""
    import math
    _, a, b = lab(hex_barwy)
    return (math.degrees(math.atan2(b, a)) + 360) % 360


def z_lab(L: float, a: float, b: float) -> str:
    """Odwrotnosc `lab` — barwa szesnastkowa z (L*, a*, b*), D65.

    DLACZEGO. Dobor „papieru cieplejszego i ciemniejszego o tyle a tyle"
    robiony na skladowych RGB jest zgadywaniem: zmiana jednego kanalu rusza
    jednoczesnie jasnosc, nasycenie i odcien. W CIELAB kazda z tych trzech
    rzeczy ma wlasna os, wiec decyzja „ciemniej o 3 L*, cieplej o 5 C*,
    odcien bez zmian" da sie zapisac liczba i sprawdzic pomiarem zwrotnym.
    """
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def g(f):
        return f ** 3 if f ** 3 > 216 / 24389 else (116 * f - 16) / (24389 / 27)

    x, y, z = (k * w for k, w in zip((g(fx), g(fy), g(fz)), BIALY_D65))
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    zi = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    n = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return "#" + "".join(f"{round(max(0.0, min(1.0, _do_sRGB(max(0.0, min(1.0, k))))) * 255):02X}"
                         for k in (r, zi, n))


if __name__ == "__main__":
    if len(sys.argv) == 4:
        print(f"{stosunek(sys.argv[1], sys.argv[2]):.2f}:1  "
              f"prog {sys.argv[3]}:1  "
              f"{_werdykt(stosunek(sys.argv[1], sys.argv[2]), float(sys.argv[3]))}")
    else:
        print("uzycie: kontrast.py <barwa> <tlo> <prog>")
