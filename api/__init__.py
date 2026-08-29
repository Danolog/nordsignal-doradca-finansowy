# -*- coding: utf-8 -*-
"""Pakiet warstwy sieciowej — PLIK ISTNIEJE CELOWO, nie jest pusty przez zaniedbanie.

Do W6 (2026-08-29) `api/` dzialalo jako pakiet przestrzeni nazw (namespace
package): katalog bez `__init__.py`, ktory Python i tak importuje. Lokalnie to
dziala, bo katalog projektu jest pierwszy na sciezce wyszukiwania. W funkcji
Vercela sciezka wyszukiwania jest inna — budowniczy Pythona kopiuje pliki do
`/var/task` i uruchamia handler z innego katalogu roboczego. Pakiet przestrzeni
nazw rozstrzyga sie wtedy przez SKANOWANIE calej sciezki, a nie przez jeden
katalog, i wystarczy jeden inny katalog o nazwie `api` wczesniej na sciezce,
zeby `from api import trasy_plynnosc` przynioslo cudzy modul.

CO PRZEZ TO PRZESTANIE DZIALAC: nic. Pakiet zwykly obsluguje wszystko, co
obslugiwal pakiet przestrzeni nazw; tracimy wylacznie mozliwosc rozbicia `api`
na kilka katalogow w roznych miejscach sciezki, ktorej nikt tu nie uzywa
(zmierzone: `api/` istnieje w jednym miejscu w repozytorium).
"""
