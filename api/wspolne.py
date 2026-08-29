# -*- coding: utf-8 -*-
"""DWIE RZECZY, KTORYCH POTRZEBUJE KAZDA TRASA — i ani jednej wiecej.

POLACZENIE JAKO ZALEZNOSC, NIE JAKO `try/finally` W KAZDEJ TRASIE. Powod nie
jest estetyczny: zasada twarda zadania Z6 brzmi „zero rachunku w trasie",
a najprostszym sposobem, zeby ta zasada byla SPRAWDZALNA, jest trasa bez
zadnego rozgalezienia. Ciato trasy skladajace sie z jednego `return` da sie
przeczytac wzrokiem i zmierzyc maszynowo (straznik
`testy/test_trasy_bez_rachunku.py`); trasa z `try/except/finally` juz nie.

POLACZENIE NA ZADANIE, nie na proces. Aplikacja jest jednoosobowa, a trasy
synchroniczne biegna w puli watkow — polaczenie wspoldzielone miedzy nimi
byloby drugim pisarzem tego samego obszaru.
"""

from __future__ import annotations

from datetime import date

from silnik.rdzen import magazyn


def polaczenie():
    """Zaleznosc FastAPI: otwiera baze na czas zadania i zamyka ja zawsze.

    Ktora baze — rozstrzyga JEDYNY nosnik tej odpowiedzi,
    `magazyn.adres_bazy()` (zmienna `DATABASE_URL`), razem z bramka, ktora
    pod pytestem odmawia otwarcia bazy spoza bazy testowej. Warstwa sieciowa
    nie ma tu wlasnego zdania.

    OD W4 (2026-08-29) BAZA JEST ADRESEM, NIE PLIKIEM. Zmienilo to koszt tej
    zaleznosci: otwarcie polaczenia do serwera trwa dluzej niz otwarcie pliku,
    a liczba jednoczesnych sesji jest u dostawcy zasobem z limitem. Aplikacja
    jest jednoosobowa, wiec „polaczenie na zadanie" nadal sie broni — ale
    jesli zaczna sie limity sesji, TU jest miejsce na pule polaczen, nie
    w silniku.
    """
    otwarte = magazyn.polacz()
    try:
        yield otwarte
    finally:
        otwarte.close()


def dzien(surowy: "str | None") -> date:
    """Dzien odniesienia — JEDEN NOSNIK odpowiedzi „kiedy jest dzis".

    Parametr istnieje dla POMIARU ODBIORCZEGO: bez niego kryterium „ta sama
    liczba z silnika i z HTTP" jest niesprawdzalne w dniu innym niz dzisiejszy,
    a bramka Z7 („prognoza po wpisie jest inna niz przed") wymaga ustalonego
    dnia, zeby jej wynik nie zalezal od godziny przebiegu.
    """
    return date.fromisoformat(surowy) if surowy else date.today()
