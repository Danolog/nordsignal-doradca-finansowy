# -*- coding: utf-8 -*-
"""Straznik granic miedzy warstwami — przeniesiony z poprzednika i poszerzony.

Bez niego opcja „silnik zyje dalej niz ten interfejs" wygasa po trzeciej
sesji, bo nikt o niej nie pamieta. Reguly pilnowanej dobra wola nie ma.

DWIE GRANICE, NIE JEDNA:

  1. NIC z warstwy interfejsu w silniku, warstwie HTTP i wiedzy. W poprzedniku
     chodzilo o `nicegui`: warstwa HTTP, ktora go zaimportuje, dostaje
     w zasieg reki `NiceGUIJSONResponse` — czyli aktywnego przeciwnika reguly
     groszowej, bo zamienia `Decimal` na liczbe zmiennoprzecinkowa, gubi
     grosze i ZWRACA 200. Nazwy zostaja na liscie mimo wygaszenia starej
     aplikacji: straznik na NIEOBECNOSC ma sens dopoty, dopoki rzecz da sie
     przywrocic jednym importem.

  2. ZERO WEB FRAMEWORKU W SILNIKU — granica dolozona w tym projekcie (Z4).
     `silnik/` ma nie wiedziec, ze istnieje HTTP. To jest warunek zadania Z6
     („zero rachunku w warstwie sieciowej") widziany z drugiej strony:
     dopoki silnik nie zna `fastapi`, nie ma jak wciagnac do siebie ani
     serializacji, ani kodu odpowiedzi. `api/` ma prawo importowac `fastapi`
     i dlatego ta druga reguła obejmuje WYLACZNIE `silnik/`.
"""

import ast
import pathlib

import pytest

KORZEN = pathlib.Path(__file__).resolve().parent.parent
SILNIK = KORZEN / "silnik"
API = KORZEN / "api"
WIEDZA = KORZEN / "wiedza"

ZAKAZANE_WSZEDZIE = {"nicegui", "webview", "pulpit"}
ZAKAZANE_W_SILNIKU = {"fastapi", "uvicorn", "starlette"}

PLIKI = sorted(
    (p for korzen in (SILNIK, API, WIEDZA) for p in korzen.rglob("*.py")
     if p.name != "__init__.py"),
    key=lambda p: str(p))


def _etykieta(p: pathlib.Path) -> str:
    return str(p.relative_to(KORZEN))


def _importowane_moduly(plik: pathlib.Path) -> set[str]:
    drzewo = ast.parse(plik.read_text(encoding="utf-8"))
    nazwy: set[str] = set()
    for wezel in ast.walk(drzewo):
        if isinstance(wezel, ast.Import):
            nazwy.update(a.name.split(".")[0] for a in wezel.names)
        elif isinstance(wezel, ast.ImportFrom):
            if wezel.module:
                nazwy.add(wezel.module.split(".")[0])
    return nazwy


@pytest.mark.parametrize("plik", PLIKI, ids=_etykieta)
def test_silnik_api_i_wiedza_nie_importuja_interfejsu(plik):
    uzyte = _importowane_moduly(plik) & ZAKAZANE_WSZEDZIE
    assert not uzyte, (
        f"{_etykieta(plik)} importuje {sorted(uzyte)}. Silnik, warstwa HTTP "
        f"i wiedza maja byc niezalezne od interfejsu — to warunek pozniejszego "
        f"portu na inny front, a dla `api/` takze jedyna obrona przed klasa "
        f"odpowiedzi, ktora zamienia Decimal na liczbe zmiennoprzecinkowa.")


@pytest.mark.parametrize(
    "plik", [p for p in PLIKI if SILNIK in p.parents], ids=_etykieta)
def test_silnik_nie_wie_o_istnieniu_HTTP(plik):
    uzyte = _importowane_moduly(plik) & ZAKAZANE_W_SILNIKU
    assert not uzyte, (
        f"{_etykieta(plik)} importuje {sorted(uzyte)}. Silnik liczy; HTTP "
        f"mieszka w `api/`. Import web frameworku do silnika jest pierwszym "
        f"krokiem do przeniesienia rachunku do trasy.")


def test_straznik_widzi_wiecej_niz_ZERO_plikow():
    """Kontrola licznosci. Gdyby glob przestal cokolwiek zwracac — bo ktos
    przeniosl katalog albo zmienil nazwe — parametryzacja bylaby pusta,
    a suita zielona. Sprawdzenie, do ktorego nic nie dociera, melduje sukces.
    """
    assert len(PLIKI) >= 20, f"straznik widzi tylko {len(PLIKI)} plikow"
    for korzen, nazwa in ((SILNIK, "silnik"), (API, "api"), (WIEDZA, "wiedza")):
        assert [p for p in PLIKI if korzen in p.parents], \
            f"straznik nie widzi ANI JEDNEGO pliku w `{nazwa}/`"


def test_straznik_naprawde_czyta_importy():
    """Kontrola dwustronna: mechanizm dziala na czyms, o czym wiemy, ze tam jest.

    Bez niej `_importowane_moduly` mogloby zwracac pusty zbior zawsze
    (zla sciezka, cichy wyjatek) i wszystkie asercje wyzej przechodzilyby.
    """
    assert "decimal" in _importowane_moduly(SILNIK / "rdzen" / "stawki.py")
    assert "silnik" in _importowane_moduly(SILNIK / "rdzen" / "podatki.py")
    # Po W4 magazyn importuje sterownik PostgreSQL. Ten wiersz jest kontrola
    # dwustronna mechanizmu (czy parser w ogole cokolwiek widzi), a przy
    # okazji straznikiem tego, ze sterownik jest DOKLADNIE JEDEN: `sqlite3`
    # nie ma prawa wrocic do silnika tylnymi drzwiami.
    importy = _importowane_moduly(SILNIK / "rdzen" / "magazyn.py")
    assert "psycopg" in importy
    assert "sqlite3" not in importy, (
        "magazyn importuje sterownik SQLite — po W4 baza jest PostgreSQL, "
        "a dwa sterowniki naraz znaczyloby dwa zachowania tej samej funkcji")
