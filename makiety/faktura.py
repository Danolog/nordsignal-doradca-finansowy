"""Pomiar faktury na ZRENDEROWANEJ planszy, nie na modelu warstw.

DLACZEGO NA ZRENDEROWANEJ. `kontrast.skrajne_faktury` sklada warstwy plaskie
i zaklada, ze kazda albo lezy w pelnym kryciu, albo jej nie ma. Szum SVG ma
wlasny kanal alfa, wiec model daje granice teoretyczna, a nie to, co widzi oko.

TRZY KONTROLE, kazda z powodem z wpadki, ktora ja zrodzila:
  K1 (z v0.4) — plansza nie moze byc jednolita: liczba roznych barw > 50.
  K2 (NOWA)   — najciemniejszy i najjasniejszy punkt musza SIE ROZNIC
                o mierzalna wartosc: dL* >= prog. Plansza „wszystko prawie
                biale" ma tu przepasc, a nie przejsc jako sukces.
  K3 (NOWA)   — faktura musi byc DWUSTRONNA: czesc pikseli ciemniejsza od bazy
                i czesc jasniejsza. Sama warstwa rozjasniajaca to nie faktura,
                tylko ruch w strone bieli — to jest wada zglaszona przez Darka
                i K3 jest jej maszynowym odpowiednikiem.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
from png import wczytaj
from kontrast import luminancja, lab, stosunek, roznica_lab
from render import zrzut

SZABLON = """<!doctype html><html><head><meta charset="utf-8"></head>
<body style="margin:0"><div style="{styl} width:1440px; height:900px;"></div></body></html>"""


def hx(px):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(k)))) for k in px[:3])


def _lum_tablica(o):
    s = o.astype(np.float64) / 255.0
    lin = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[:, :, 0] + 0.7152 * lin[:, :, 1] + 0.0722 * lin[:, :, 2]


def zmierz_plansze(styl, baza, katalog, nazwa, obszar=None, prog_dL=0.6):
    html = pathlib.Path(katalog) / f"plansza-{nazwa}.html"
    png = pathlib.Path(katalog) / f"plansza-{nazwa}.png"
    html.write_text(SZABLON.format(styl=styl), encoding="utf-8")
    zrzut(str(html), str(png), pelna=False)
    o = wczytaj(str(png))
    if obszar:
        y0, y1, x0, x1 = obszar
        o = o[y0:y1, x0:x1]
    plaskie = o.reshape(-1, 3)
    u = np.unique(plaskie, axis=0)
    L = _lum_tablica(o)
    ic, ij = np.unravel_index(L.argmin(), L.shape), np.unravel_index(L.argmax(), L.shape)
    najciemniejszy, najjasniejszy = hx(o[ic]), hx(o[ij])
    Lb = luminancja(baza)
    ciemniejszych = float((L < Lb - 1e-6).mean())
    jasniejszych = float((L > Lb + 1e-6).mean())
    srednia = hx(plaskie.mean(axis=0).round())
    dL = lab(najjasniejszy)[0] - lab(najciemniejszy)[0]
    wynik = {
        "nazwa": nazwa, "baza": baza, "barw": int(len(u)),
        "najciemniejszy": najciemniejszy, "najjasniejszy": najjasniejszy,
        "srednia": srednia,
        "rozpietosc_stosunek": stosunek(najciemniejszy, najjasniejszy),
        "rozpietosc_dL": dL,
        "dryf_sredniej_dE": roznica_lab(srednia, baza),
        "udzial_ciemniejszych": ciemniejszych, "udzial_jasniejszych": jasniejszych,
        "K1_niejednolita": len(u) > 50,
        "K2_rozpietosc": dL >= prog_dL,
        "K3_dwustronna": ciemniejszych >= 0.15 and jasniejszych >= 0.15,
    }
    return wynik


def wypisz(w):
    print(f"--- PLANSZA {w['nazwa']}  (baza {w['baza']}) ---")
    print(f"  barw roznych            {w['barw']}")
    print(f"  najciemniejszy punkt    {w['najciemniejszy']}")
    print(f"  najjasniejszy punkt     {w['najjasniejszy']}")
    print(f"  srednia planszy         {w['srednia']}   dryf od bazy dE = {w['dryf_sredniej_dE']:.2f}")
    print(f"  ROZPIETOSC faktury      {w['rozpietosc_stosunek']:.4f}:1   dL* = {w['rozpietosc_dL']:.2f}")
    print(f"  pikseli ciemniejszych od bazy  {w['udzial_ciemniejszych']*100:6.2f}%")
    print(f"  pikseli jasniejszych  od bazy  {w['udzial_jasniejszych']*100:6.2f}%")
    for k in ("K1_niejednolita", "K2_rozpietosc", "K3_dwustronna"):
        print(f"  {k:22s} {'OK' if w[k] else 'PADA'}")
    if not (w["K1_niejednolita"] and w["K2_rozpietosc"] and w["K3_dwustronna"]):
        print("  >>> POMIAR NIE ZALICZA TEJ PLANSZY JAKO FAKTURY <<<")


def spektrum(png, baza, skale=(1, 2, 4, 8, 16, 64), obszar=None):
    """Rozpietosc faktury W SKALACH PRZESTRZENNYCH — bo oko nie widzi pojedynczego piksela.

    Szum o amplitudzie rozlozonej na pojedyncze piksele znika po usrednieniu
    przez oko (ok. 1 minuta katowa; na laptopie z 60 cm to ~1,5 px). Faktura,
    ktora ma byc WIDZIANA jako faktura, musi miec amplitude w skali ~8-16 px.
    Plama swiatla siedzi w skali 64 px i wyzej — i to ona daje wrazenie
    „jasniejszego ekranu", nie faktura.
    """
    o = wczytaj(png)
    if obszar:
        y0, y1, x0, x1 = obszar
        o = o[y0:y1, x0:x1]
    wynik = []
    for n in skale:
        h, w = (o.shape[0] // n) * n, (o.shape[1] // n) * n
        blok = o[:h, :w].reshape(h // n, n, w // n, n, 3).mean(axis=(1, 3))
        L = _lum_tablica(blok)
        ic = np.unravel_index(L.argmin(), L.shape)
        ij = np.unravel_index(L.argmax(), L.shape)
        c, j = hx(blok[ic].round()), hx(blok[ij].round())
        wynik.append((n, c, j, lab(j)[0] - lab(c)[0]))
    return wynik


def wypisz_spektrum(nazwa, w):
    print(f"--- ROZPIETOSC W SKALACH, plansza {nazwa} ---")
    print("  skala   najciemniejszy  najjasniejszy   dL*")
    for n, c, j, d in w:
        etykieta = {1: "  <- pojedynczy piksel, oko tego nie widzi",
                    8: "  <- SKALA WIDZENIA FAKTURY",
                    64: "  <- skala plam swiatla"}.get(n, "")
        print(f"  {n:3d}px   {c}        {j}       {d:5.2f}{etykieta}")


def rozklad(png, obszar=None, skala_plamy=64, skala_oka=8):
    """Rozdziela fakture na PLAME (wielka skala) i WLOKNO (skala widzenia).

    PLAMA  = rozpietosc srednich blokow `skala_plamy` — to jest „jasniejszy ekran".
    WLOKNO = rozpietosc reszty po odjeciu plamy, mierzona w blokach `skala_oka`.
    PYL    = rozpietosc na pojedynczym pikselu po odjeciu obu — oko tego nie widzi.
    """
    o = wczytaj(png).astype(np.float64)
    if obszar:
        y0, y1, x0, x1 = obszar
        o = o[y0:y1, x0:x1]

    def bloki(a, n):
        h, w = (a.shape[0] // n) * n, (a.shape[1] // n) * n
        return a[:h, :w].reshape(h // n, n, w // n, n, 3).mean(axis=(1, 3))

    def rozpietosc(a):
        L = _lum_tablica(a)
        ic = np.unravel_index(L.argmin(), L.shape)
        ij = np.unravel_index(L.argmax(), L.shape)
        return lab(hx(a[ij].round()))[0] - lab(hx(a[ic].round()))[0]

    n, m = skala_plamy, skala_oka
    h, w = (o.shape[0] // n) * n, (o.shape[1] // n) * n
    o = o[:h, :w]
    plama = bloki(o, n)
    plama_pelna = np.repeat(np.repeat(plama, n, axis=0), n, axis=1)
    reszta = o - plama_pelna + 245.0          # wracam na poziom papieru, zeby L* mialo sens
    wlokno = bloki(reszta, m)
    return {
        "plama_dL": rozpietosc(plama),
        "wlokno_dL": rozpietosc(wlokno),
        "pyl_dL": rozpietosc(reszta - np.repeat(np.repeat(wlokno, m, axis=0), m, axis=1) + 245.0),
        "calosc_dL": rozpietosc(o),
    }


def wypisz_rozklad(nazwa, r):
    print(f"--- ROZKLAD FAKTURY, {nazwa} ---")
    print(f"  PLAMA  (bloki 64 px, jasniejszy ekran)     dL* = {r['plama_dL']:5.2f}")
    print(f"  WLOKNO (bloki  8 px, to co widac)          dL* = {r['wlokno_dL']:5.2f}")
    print(f"  PYL    (pojedynczy piksel, niewidoczny)    dL* = {r['pyl_dL']:5.2f}")
    print(f"  calosc                                     dL* = {r['calosc_dL']:5.2f}")
