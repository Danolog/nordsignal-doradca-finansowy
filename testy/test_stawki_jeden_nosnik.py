# -*- coding: utf-8 -*-
"""Straznik S2: stawki i progi maja DOKLADNIE JEDEN nosnik (Z4 krok 4.5).

POWOD ISTNIENIA — ZMIERZONY ROZJAZD, NIE HIPOTEZA. Do przenosin tabela progow
skladki zdrowotnej stala w DWOCH miejscach: w `stawki.PROGI_ZDROWOTNEJ`
i jako przepisany `if/elif` w `formy.py`, z komentarzem „ta sama tabela co
w rdzen.podatki". Nie byla ta sama. Przy przychodzie DOKLADNIE 300 000 zl:

    nosnik  (`stawki.prog_dla_przychodu`)  -> mnoznik 1,80
    kopia   (`formy.py`, `elif <= 300000`) -> mnoznik 1,00

Roznica w skladce zdrowotnej: 1 495,04 zl wobec 830,58 zl miesiecznie, czyli
664,46 zl na miesiac i 7 973,52 zl na rok — na korzysc ryczaltu, czyli
w strone, w ktora porownanie form ma NIE byc stronnicze. Zadnego straznika
tam nie bylo; 641 testow przechodzilo na zielono po obu stronach naprawy.

CZEGO TEN PLIK PILNUJE — trzy pytania, nie jedno:
  1. czy obie sciezki wybieraja ten sam prog NA GRANICACH przedzialow;
  2. czy tabela progow nie zostala odtworzona w zadnym module liczacym;
  3. czy kazda stawka uzyta w porownaniu form ma wpis w rejestrze stawek.

KONTROLA LICZNOSCI. Kazdy straznik zrodlowy ponizej najpierw stwierdza, ILE
plikow zobaczyl. Sprawdzenie, do ktorego nic nie dociera, MELDUJE SUKCES —
a przeszukanie po zlej sciezce wyglada dokladnie tak samo jak brak trafien.
"""

import re
from decimal import Decimal
from pathlib import Path

import pytest

from silnik.rdzen import formy, podatki, stawki
from wiedza import stawki_poczatkowe

KORZEN = Path(__file__).resolve().parent.parent
MIESIECY = 12

#: Granice obu przedzialow, z obu stron. Wartosc 300000 jest tu najwazniejsza:
#: dokladnie na niej kopie sie rozjezdzaly, i dokladnie jej nie dotykal zaden
#: z 591 przeniesionych testow.
GRANICE = ["0", "59999.99", "60000", "60000.01",
           "299999.99", "300000", "300000.01", "1000000"]


# --- 1. obie sciezki, ten sam prog ----------------------------------------

@pytest.mark.parametrize("przychod", GRANICE)
def test_podatki_i_stawki_daja_TEN_SAM_prog(przychod):
    """`podatki.prog_dla_przychodu` ma WOLAC nosnik, nie liczyc samo."""
    x = Decimal(przychod)
    assert podatki.prog_dla_przychodu(x) == stawki.prog_dla_przychodu(x)


@pytest.mark.parametrize("przychod", GRANICE)
def test_porownanie_form_liczy_zdrowotna_Z_NOSNIKA(przychod):
    """Straznik BEHAWIORALNY, nie zrodlowy.

    Pyta o LICZBE, ktora wyszla z porownania form, a nie o ksztalt kodu.
    Straznik zrodlowy („czy w pliku jest `if przychod <`") przepuscilby kopie
    zapisana inaczej — na przyklad slownikiem albo `bisect`. Ta asercja
    czerwieni sie na KAZDEJ kopii, ktora wybiera inny prog.
    """
    x = Decimal(przychod)
    oczekiwana = stawki.do_zlotych(
        stawki.skladka_zdrowotna(stawki.mnoznik_dla_przychodu(x)) * MIESIECY)
    ryczalty = [w for w in formy.porownaj_formy(x, MIESIECY)
                if w.nazwa.startswith("ryczalt")]
    assert len(ryczalty) == 2, (
        f"kontrola licznosci: porownanie zwrocilo {len(ryczalty)} form "
        f"ryczaltu zamiast dwoch — straznik mierzylby pusty zbior")
    for w in ryczalty:
        assert w.zdrowotna == oczekiwana, (
            f"{w.nazwa} przy przychodzie {przychod}: skladka zdrowotna "
            f"{w.zdrowotna} zamiast {oczekiwana}. Prog policzony inna tabela "
            f"niz `stawki.PROGI_ZDROWOTNEJ` — kopia wrocila.")


def test_granica_300000_jest_MIEJSCEM_w_ktorym_kopie_sie_rozjechaly():
    """Kontrola dwustronna do testu wyzej: pilnuje, ze wartosc 300 000 zl
    faktycznie ROZDZIELA dwa progi. Gdyby kiedys przestala (bo zmienil sie
    przepis), test wyzej nadal by przechodzil, ale przestalby cokolwiek
    znaczyc — mierzylby granice, ktorej nie ma."""
    ponizej = stawki.mnoznik_dla_przychodu(Decimal("299999.99"))
    na_granicy = stawki.mnoznik_dla_przychodu(Decimal("300000"))
    assert ponizej != na_granicy, (
        "300 000 zl nie jest juz granica progu — ten plik mierzy wartosc, "
        "ktora przestala cokolwiek rozdzielac")
    assert na_granicy == Decimal("1.80")


# --- 2. tabela progow nie zostala odtworzona ------------------------------

def _moduly_liczace() -> list[Path]:
    pliki = sorted(KORZEN.glob("silnik/**/*.py")) + sorted(KORZEN.glob("api/*.py"))
    assert len(pliki) >= 20, (
        f"kontrola licznosci: straznik widzi tylko {len(pliki)} plikow — "
        f"sciezka jest zla, a zero trafien wygladaloby jak sukces")
    return pliki


def test_progi_zdrowotnej_maja_JEDEN_nosnik():
    """Liczby 60000 i 300000 wolno trzymac wylacznie w `stawki.py`."""
    pliki = _moduly_liczace()
    z_progami = [p.name for p in pliki
                 if re.search(r'Decimal\("(60000|300000)"\)',
                              p.read_text(encoding="utf-8"))]
    assert z_progami == ["stawki.py"], (
        f"progi skladki zdrowotnej przepisane zamiast zawolane: {z_progami}")


def test_mnozniki_progow_maja_JEDEN_nosnik():
    """Mnozniki 0,60 / 1,00 / 1,80 — ta sama regula, druga polowa tabeli.

    Osobno od testu wyzej SWIADOMIE: kopia potrafi przepisac same mnozniki,
    a progi zawolac — i wtedy jedna asercja na obie polowy przechodzi.
    """
    pliki = _moduly_liczace()
    wzorzec = re.compile(r'Decimal\("(0\.60|1\.00|1\.80)"\)')
    z_mnoznikami = [p.name for p in pliki
                    if wzorzec.search(p.read_text(encoding="utf-8"))]
    assert z_mnoznikami == ["stawki.py"], (
        f"mnozniki podstawy zdrowotnej przepisane zamiast zawolane: "
        f"{z_mnoznikami}")


def test_formy_nie_ma_ANI_JEDNEGO_literalu_stawki():
    """`formy.py` jest modulem LICZACYM. Regula `CLAUDE.md` §3.3 nie zna
    wyjatku „to tylko do porownania"."""
    zrodlo = (KORZEN / "silnik" / "rdzen" / "formy.py").read_text(encoding="utf-8")
    assert len(zrodlo) > 1000, "kontrola licznosci: straznik czyta pusty plik"
    literaly = re.findall(r'Decimal\("(0\.\d+|\d{4,}(?:\.\d+)?)"\)', zrodlo)
    assert literaly == [], (
        f"literaly stawek wrocily do `formy.py`: {literaly}. Kazda liczba "
        f"z ustawy mieszka w rejestrze stawek, nie w kodzie liczacym.")


# --- 3. stawki porownania sa w rejestrze ----------------------------------

def test_kazda_stawka_ryczaltu_z_porownania_ma_wpis_w_REJESTRZE():
    """Rejestr ma niesc KAZDA stawke, ktorej silnik uzywa — inaczej czesc
    liczb zyje poza nim i reguła „automat proponuje, czlowiek zatwierdza"
    obejmuje tylko te, ktore ktos pamietal wpisac."""
    w_rejestrze = {s.klucz: s.wartosc for s in stawki_poczatkowe.WSZYSTKIE}
    assert len(w_rejestrze) >= 15, (
        f"kontrola licznosci: rejestr ma {len(w_rejestrze)} pozycji")
    uzywane = [s for s, _ in stawki.STAWKI_RYCZALTU_DO_POROWNANIA]
    assert len(uzywane) == 2, "porownanie form uzywa innej liczby stawek niz dwie"
    ryczaltowe = {k: v for k, v in w_rejestrze.items() if k.startswith("ryczalt.")}
    for stawka in uzywane:
        assert stawka in ryczaltowe.values(), (
            f"stawka ryczaltu {stawka} uzywana przez `formy.porownaj_formy` "
            f"nie ma wpisu w rejestrze; sa tam: {sorted(ryczaltowe)}")


def test_rejestr_nie_upowaznia_do_liczenia_ryczaltem():
    """Kontrola dwustronna do testu wyzej. Obecnosc stawek ryczaltu
    w rejestrze nie ma sie zamienic w ciche pozwolenie: Darek jest na SKALI
    (`CLAUDE.md` §2), a ryczalt wracal w poprzedniku wlasnie jako wartosc
    domyslna. Kazdy wpis ryczaltowy ma to mowic wprost."""
    ryczaltowe = [s for s in stawki_poczatkowe.WSZYSTKIE
                  if s.klucz.startswith("ryczalt.")]
    assert len(ryczaltowe) == 2, (
        f"kontrola licznosci: {len(ryczaltowe)} wpisow ryczaltowych")
    for s in ryczaltowe:
        assert "PORÓWNANIE FORM" in s.opis, (
            f"{s.klucz} nie mowi, ze sluzy wylacznie porownaniu form")
        assert s.status == "proponowana", (
            f"{s.klucz} ma status {s.status!r} — zadna stawka nie wchodzi "
            f"jako zatwierdzona bez podpisu Darka")


# --- 4. zaokraglenie ma jeden nosnik (krok 4.4) ---------------------------

def test_zaokraglenie_ma_JEDEN_nosnik_i_jest_nim_pieniadz():
    """`stawki.do_groszy` ma WOLAC `pieniadz.do_groszy`, nie liczyc samo.

    Straznik zrodlowy („czy w pliku jest slowo `pieniadz`") tego nie dowodzi —
    import moglby istniec obok wlasnej kopii `quantize`. Dowodzi tego
    ZACHOWANIE, ktorego kopia nie ma: `pieniadz.zabron_float` ODMAWIA przyjecia
    liczby zmiennoprzecinkowej, a poprzednia wersja `stawki.do_groszy`
    konwertowala ja po cichu przez `Decimal(x)`.

    ZAKRES: ten test mowi o `stawki.do_groszy` i `stawki.do_zlotych`, NIE
    o calej aplikacji. Zdanie „zaokraglenie ma jeden nosnik w calym
    projekcie" nie ma pokrycia w tym pliku — patrz sprostowanie przy
    `test_kwota_nie_jest_liczona_wlasnym_quantize_poza_pieniadzem` nizej.
    """
    from silnik import pieniadz

    assert stawki.do_groszy(Decimal("1.005")) == Decimal("1.01")
    assert stawki.do_zlotych(Decimal("1.5")) == Decimal("2")
    for funkcja in (stawki.do_groszy, stawki.do_zlotych, pieniadz.do_groszy):
        with pytest.raises(TypeError) as blad:
            funkcja(0.1)
        assert "zmiennoprzecinkowa" in str(blad.value), (
            "komunikat ma mowic, CO jest zle — inaczej wolajacy zamieni "
            "liczbe na napis i pojdzie dalej")


def test_kwota_nie_jest_liczona_wlasnym_quantize_poza_pieniadzem():
    """Kontrola zrodlowa: wywolanie `quantize` na groszach i zlotych wolno
    postawic wylacznie w `silnik/pieniadz.py`.

    CZEGO TEN TEST NIE DOWODZI — sprostowanie po przegladzie Z10 (Leo,
    2026-08-29). Do tego dnia byl przywolywany jako dowod, ze zaokraglenie
    kwoty ma JEDEN NOSNIK. **Nie jest takim dowodem i nigdy nie byl.**

    Szuka wylacznie KSZTALTU `quantize(...)`. Python zaokragla takze przez
    OPIS FORMATU — `f"{x:,.2f}"` — i tego ksztaltu ten wzorzec nie widzi.
    Zmierzone mutacja M-L7: podstawienie drugiego nosnika zaokraglenia przez
    opis formatu w `prognoza_plynnosci.py` dalo `892 passed, 3 deselected` —
    ANI JEDNEJ CZERWIENI. Ten test przeszedl mutacje, ktora lamala regule,
    o ktorej pilnowanie byl podejrzewany.

    ZAKRES, PO SPROSTOWANIU: „nikt nie wola `quantize` poza `pieniadz.py`".
    Tyle i tylko tyle. Drugiego ksztaltu — opisu formatu — pilnuje OSOBNY
    plik `testy/test_zaokraglenie_ekranu.py`, dopisany przez Leo w tym samym
    przegladzie; tam jest tez mutacja, ktora go czerwieni.

    Wyjatek nazwany: `budzet.py` zaokragla PROCENTY do jednego miejsca
    (`_DZIESIETNA`), a to nie jest kwota. Straznik pyta o kwotowe kwantyzatory
    `Decimal("0.01")` i `Decimal("1")`, nie o samo slowo `quantize`.
    """
    pliki = _moduly_liczace()
    wzorzec = re.compile(r'quantize\(\s*(?:GROSZ|ZLOTY|Decimal\("(?:0\.01|1)"\))')
    z_kwantyzacja = sorted({p.name for p in pliki
                            if wzorzec.search(p.read_text(encoding="utf-8"))})
    assert z_kwantyzacja == ["pieniadz.py"], (
        f"zaokraglanie kwot poza jedynym nosnikiem: {z_kwantyzacja}")
