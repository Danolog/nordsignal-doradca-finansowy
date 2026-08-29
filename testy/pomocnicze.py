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
