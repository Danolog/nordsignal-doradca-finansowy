# -*- coding: utf-8 -*-
"""STRAZNIK ZASADY TWARDEJ Z6: ZERO RACHUNKU W WARSTWIE SIECIOWEJ.

DLACZEGO TO JEST STRAZNIK, A NIE ZAPEWNIENIE W NAGLOWKU. Zdanie „trasa wola
silnik i zwraca wynik" stalo w naglowku `api/trasy.py` od poczatku i nie
przeszkodzilo niczemu — bo nagl'owek niczego nie sprawdza. Kwota policzona
w trasie jest DRUGIM NOSNIKIEM reguly, ktora ma juz swoj; rozjazd miedzy nimi
wychodzi na jaw dopiero wtedy, gdy ekran i silnik podaja dwie rozne liczby
o tej samej rzeczy w tej samej chwili (zmierzone u poprzednika 2026-08-26:
-6 098,11 zl na ekranie wobec +8 007,89 zl u doradcy).

CO DOKLADNIE JEST ZAKAZANE W CIELE TRASY: rozgalezienie (`if`, `if/else`
w wyrazeniu, `and`/`or`), petla i wyrazenie skladane, `try`, przypisanie oraz
KAZDE dzialanie arytmetyczne i porownanie. Zostaje jedno `return` z wywolaniem
silnika. To jest kryterium maszynowe, nie ocena stylu — i wlasnie dlatego
wolno sie na nie powolac.

CZEGO TEN STRAZNIK NIE PILNUJE — jawnie. Nie pilnuje, ze funkcja WOLANA przez
trase liczy poprawnie; to robia strazniki silnika. Nie pilnuje tez tras spoza
`api/trasy_*.py` — plik `api/index.py` niesie punkt kontrolny `/api/zdrowie`
i jest z tego zakresu wylaczony swiadomie, bo nie dotyka ani jednej kwoty.
"""

import ast
import pathlib

import pytest

KORZEN = pathlib.Path(__file__).resolve().parent.parent
PLIKI_TRAS = sorted((KORZEN / "api").glob("trasy_*.py"))

#: Ile tras ma stac po zadaniu Z6. Liczba jest ASERCJA, nie komentarzem:
#: straznik, ktory nie znalazl ani jednej trasy, przechodzi kazde
#: sprawdzenie „w trasach nie ma rachunku".
ILE_TRAS = 6

ZAKAZANE = {
    ast.If: "rozgałęzienie `if`",
    ast.IfExp: "wyrażenie warunkowe `a if b else c`",
    ast.BoolOp: "`and` / `or`",
    ast.For: "pętla `for`",
    ast.While: "pętla `while`",
    ast.Try: "`try`",
    ast.Assign: "przypisanie",
    ast.AugAssign: "przypisanie z działaniem",
    ast.BinOp: "działanie arytmetyczne",
    ast.UnaryOp: "działanie jednoargumentowe",
    ast.Compare: "porównanie",
    ast.ListComp: "wyrażenie składane",
    ast.DictComp: "wyrażenie składane",
    ast.SetComp: "wyrażenie składane",
    ast.GeneratorExp: "wyrażenie składane",
}


def _trasy() -> list[tuple[str, ast.FunctionDef]]:
    """Funkcje udekorowane `@trasy.<metoda>(...)` we wszystkich plikach tras."""
    znalezione = []
    for plik in PLIKI_TRAS:
        drzewo = ast.parse(plik.read_text(encoding="utf-8"))
        for wezel in ast.walk(drzewo):
            if not isinstance(wezel, ast.FunctionDef):
                continue
            for dekorator in wezel.decorator_list:
                cel = dekorator.func if isinstance(dekorator, ast.Call) else dekorator
                if isinstance(cel, ast.Attribute) and cel.attr in (
                        "get", "post", "put", "delete"):
                    znalezione.append(
                        (f"{plik.name}::{wezel.name}", wezel))
    return znalezione


def test_straznik_widzi_DOKLADNIE_szesc_tras():
    """Kontrola licznosci. Bez niej parametryzacja mogla by byc pusta —
    a przebieg bez ani jednego przypadku melduje sukces."""
    assert [p.name for p in PLIKI_TRAS] == [
        "trasy_ksiegowanie.py", "trasy_plynnosc.py"]
    nazwy = [n for n, _ in _trasy()]
    assert len(nazwy) == ILE_TRAS, f"straznik widzi {len(nazwy)} tras: {nazwy}"


@pytest.mark.parametrize("nazwa,funkcja", _trasy(), ids=[n for n, _ in _trasy()])
def test_cialo_trasy_NIE_LICZY_niczego(nazwa, funkcja):
    winne = []
    for wezel in ast.walk(ast.Module(body=funkcja.body, type_ignores=[])):
        opis = ZAKAZANE.get(type(wezel))
        if opis:
            winne.append(f"{opis} w linii {wezel.lineno}")
    assert winne == [], (
        f"{nazwa}: rachunek w warstwie sieciowej — {winne}. Trasa ma WOLAC "
        f"silnik i zwrocic wynik; regula policzona tutaj ma tylu nosnikow, "
        f"ile tras ja wola.")


@pytest.mark.parametrize("nazwa,funkcja", _trasy(), ids=[n for n, _ in _trasy()])
def test_cialo_trasy_to_JEDNO_zdanie_return(nazwa, funkcja):
    """Docstring plus jedno `return`. Nic wiecej sie tam nie miesci."""
    istotne = [w for w in funkcja.body
               if not (isinstance(w, ast.Expr)
                       and isinstance(w.value, ast.Constant))]
    assert len(istotne) == 1 and isinstance(istotne[0], ast.Return), (
        f"{nazwa}: cialo ma {len(istotne)} zdan poza docstringiem")


def test_wykrywacz_NAPRAWDE_lapie_rachunek():
    """Kontrola dwustronna. Bez niej `ZAKAZANE` mogloby byc puste albo
    `ast.walk` mogloby nie schodzic w glab — i szesc asercji wyzej
    przechodziloby przy calkowicie zepsutym mechanizmie."""
    podejrzana = ast.parse(
        "def trasa(x):\n"
        "    return {'kwota': x * 2 if x else 0}\n").body[0]
    winne = [ZAKAZANE[type(w)] for w in ast.walk(
        ast.Module(body=podejrzana.body, type_ignores=[]))
        if type(w) in ZAKAZANE]
    assert "działanie arytmetyczne" in winne
    assert "wyrażenie warunkowe `a if b else c`" in winne
