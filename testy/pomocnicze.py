# -*- coding: utf-8 -*-
"""Wspólne narzędzia strażników zakresu ekranów.

Jeden nośnik, bo obie kopie robiłyby dokładnie to samo, a rozjazd między nimi
byłby niewidoczny: strażnik z gorszą wersją nadal meldowałby sukces.
"""
import re


def bez_komentarzy(kod: str) -> str:
    """Zdejmuje komentarze `//…` i `/*…*/`.

    Bez tego strażnik jest atrapą. Zmierzone 2026-08-29 (przebieg Z1, mutacja
    M3): skasowanie atrybutu `autoFocus` z pola kwoty dało **36 passed**, bo
    słowo stało jeszcze w komentarzu nad komponentem. Wykryła to mutacja,
    nie czytanie kodu.

    Działa w obie strony: sprawdzenie „ta fraza JEST" nie może trafiać
    w komentarz, a sprawdzenie „tej frazy NIE MA" nie może czerwienić się
    dlatego, że komentarz cytuje zakazane zdanie, żeby wyjaśnić zakaz.
    """
    kod = re.sub(r"/\*.*?\*/", " ", kod, flags=re.S)
    return re.sub(r"//[^\n]*", " ", kod)


def kod_pythona_bez_prozy(zrodlo: str) -> str:
    """Zdejmuje z kodu Pythona KOMENTARZE i DOCSTRINGI, zostawia resztę.

    DLACZEGO NIE `bez_komentarzy` I DLACZEGO NIE „usuń wszystkie napisy".
    Strażnicy jednego nośnika szukają w tym projekcie wzorca `:,.2f` — a on
    żyje WEWNĄTRZ f-napisu, czyli wewnątrz literału tekstowego. Zdjęcie
    wszystkich napisów oślepiłoby strażnika całkowicie; zostawienie prozy
    czerwieni go na własnej dokumentacji.

    Zmierzone 2026-08-29 (sprostowanie po przeglądzie Z10): dopisanie do
    nagłówka `silnik/pieniadz.py` zdania cytującego `f"{x:,.2f}"` — po to,
    żeby WYJAŚNIĆ, dlaczego ten kształt jest zakazany — zaczerwieniło DWA
    strażniki naraz. To trzecie trafienie tego wzorca w tym projekcie
    (poprzednie: M3 w Z1, M-Z7-1c w Z7).

    Granica jest więc taka: **proza wyjaśniająca regułę nie jest jej
    złamaniem; napis, którego program używa, jest.**
    """
    import ast
    import io as _io
    import tokenize

    drzewo = ast.parse(zrodlo)
    docstringi = set()
    for wezel in ast.walk(drzewo):
        if not isinstance(wezel, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        cialo = getattr(wezel, "body", None)
        if not cialo:
            continue
        pierwszy = cialo[0]
        if (isinstance(pierwszy, ast.Expr)
                and isinstance(pierwszy.value, ast.Constant)
                and isinstance(pierwszy.value.value, str)):
            docstringi.add((pierwszy.value.lineno, pierwszy.value.col_offset))

    # WYCINAMY MIEJSCA, NIE SKLADAMY OD NOWA. Sklejenie z tokenow rozrywa
    # `:,.2f`: w Pythonie 3.12+ opis formatu wewnatrz f-napisu idzie jako
    # KILKA tokenow, wiec kazde zlaczenie z separatorem gubi wzorzec, ktorego
    # straznik szuka. Zamiast tego zostawiamy tekst nietkniety i ZAMAZUJEMY
    # spacjami wylacznie zakresy komentarzy i docstringow.
    wiersze = zrodlo.splitlines(keepends=True)

    def zamaz(od_w, od_k, do_w, do_k) -> None:
        for numer in range(od_w, do_w + 1):
            wiersz = wiersze[numer - 1]
            poczatek = od_k if numer == od_w else 0
            koniec = do_k if numer == do_w else len(wiersz)
            zachowaj_koniec = wiersz[koniec:]
            wiersze[numer - 1] = (wiersz[:poczatek]
                                  + " " * max(0, koniec - poczatek)
                                  + zachowaj_koniec)

    for token in tokenize.generate_tokens(_io.StringIO(zrodlo).readline):
        if token.type == tokenize.COMMENT or (
                token.type == tokenize.STRING and token.start in docstringi):
            zamaz(token.start[0], token.start[1],
                  token.end[0], token.end[1])
    return "".join(wiersze)
