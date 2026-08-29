# -*- coding: utf-8 -*-
"""JEDEN NOSNIK SPISU TRAS — co warstwa sieciowa ma udostepniac.

DLACZEGO SPIS, A NIE SAME DEKORATORY. Ta sama lista jest potrzebna w trzech
miejscach: buduje trasy (`index.py`), pilnuje kompletnosci (straznik w
`testy/`) i odpowiada na pytanie "czy nowy interfejs moze juz wylaczyc stary"
(PRD §9). Trzy kopie rozjechalyby sie przy pierwszym dopisaniu trasy — a
wlasnie tego rodzaju rozjazd sprawil, ze poprzednia aplikacja miala dziesiec
tras i przekonanie, ze brakuje "jednej".

STAN POPRZEDNIKA, ZMIERZONY: 10 tras — osiem odczytu, dwie zapisu. Funkcja
zapisu wpisu istniala w silniku razem z transakcyjnoscia; BRAKOWALO WYLACZNIE
DROGI HTTP. Dlatego nowy interfejs byl galeria, nie aplikacja.

CZTERY OPERACJE, BEZ KTORYCH NIE DA SIE WYLACZYC STAREJ ZAKLADKI (P-1):
dodac wpis · wycofac wpis · ustawic pozycje planu · ZAKONCZYC pozycje planu.
Oznaczone `warunek_wylaczenia=True`. Straznik pilnuje, ze wszystkie cztery
istnieja — poprzednie brzmienie przekazania mowilo o dwoch i bylo NIEPELNE.

DWIE ZASADY, OBIE Z POMIARU:
  1. JEDEN PISZACY NA JEDEN OBSZAR. Zlamanie tej reguly dalo zmierzone
     400 prob -> 274 wiersze, wpisy zdublowane.
  2. ZERO RACHUNKU W WARSTWIE SIECIOWEJ. Trasa wola silnik i zwraca wynik.
     Kwota policzona w trasie jest DRUGIM NOSNIKIEM reguly.

KWOTY W ODPOWIEDZI IDA JAKO NAPIS. Zamiana `Decimal` na liczbe
zmiennoprzecinkowa gubi grosze i zwraca 200 — awaria bezglosna.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Trasa:
    metoda: str
    sciezka: str
    ekran: str
    co_robi: str
    warunek_wylaczenia: bool = False


ODCZYT = (
    Trasa("GET", "/api/plynnosc",              "plynnosc",  "ksiega dzien-pozycja-kwota-saldo, wykres, saldo minimalne"),
    Trasa("GET", "/api/plynnosc/co-mnie-czeka", "co-mnie-czeka", "pozycje do konca okna z 'za N dni'"),
    Trasa("GET", "/api/plynnosc/co-mam-zrobic", "plynnosc",  "najwyzej trzy rady z kwota — LICZY SILNIK, nie model"),
    Trasa("GET", "/api/miesiac",               "miesiac",   "piec kafelkow, na co poszly pieniadze, saldo narastajace"),
    Trasa("GET", "/api/budzet",                "budzet",    "kafelki planu, bilans, plan kontra wykonanie, cele"),
    Trasa("GET", "/api/raporty",               "raporty",   "ranking kategorii: wpisow, suma, udzial, plan, odchylenie"),
    Trasa("GET", "/api/raporty/kategoria/{nazwa}", "raporty", "rozwiniecie kategorii do pojedynczych wpisow"),
    Trasa("GET", "/api/firma",                 "firma",     "forma, daniny do zaplacenia, faktury, koszty"),
    Trasa("GET", "/api/firma/faktura/{numer}", "firma",     "rozbicie faktury na siedem pozycji"),
    Trasa("GET", "/api/majatek",               "majatek",   "wartosc netto, aktywa, zobowiazania, suma rat"),
    Trasa("GET", "/api/godziny",               "godziny",   "stawka, wpisy w okresie, ile z tego wychodzi"),
    Trasa("GET", "/api/ustawienia/kategorie",  "ustawienia", "slownik z licznikiem wpisow i znacznikiem niezbednej"),
    Trasa("GET", "/api/ustawienia/stawki",     "ustawienia", "rejestr stawek: zatwierdzone i propozycje do podpisu"),
    Trasa("GET", "/api/straznik/ostatni",      "*",         "stopka: kiedy patrzyl i co znalazl"),
    Trasa("GET", "/api/okres",                 "*",         "wybrany okres i jego granice"),
)

ZAPIS = (
    Trasa("POST",   "/api/wpisy",             "ksiegowanie", "dodac wpis", warunek_wylaczenia=True),
    Trasa("DELETE", "/api/wpisy/{id}",        "ksiegowanie", "wycofac wpis", warunek_wylaczenia=True),
    Trasa("POST",   "/api/wpisy/podglad",     "ksiegowanie", "'Co ruszy ten wpis' — skutek PRZED zapisem"),
    Trasa("PUT",    "/api/plan/{id}",         "budzet",      "ustawic albo zmienic pozycje planu", warunek_wylaczenia=True),
    Trasa("POST",   "/api/plan",              "budzet",      "dodac pozycje planu", warunek_wylaczenia=True),
    # ZAKONCZYC, nie SKASOWAC (Z-9). Kosz przy pozycji planu KONCZY REGULE od
    # biezacego miesiaca w przod; historii nie rusza. Funkcja kasujaca istnieje
    # w silniku i jest SWIADOMIE odcieta od interfejsu. Nowa aplikacja ma to
    # zachowanie PRZEJAC, nie "naprawic".
    Trasa("POST",   "/api/plan/{id}/zakoncz", "budzet",      "zakonczyc regule planu od biezacego miesiaca", warunek_wylaczenia=True),
    Trasa("POST",   "/api/plan/kopiuj",       "budzet",      "skopiowac plan z poprzedniego miesiaca"),
    Trasa("POST",   "/api/cele",              "budzet",      "dodac cel oszczednosciowy"),
    Trasa("POST",   "/api/firma/faktury",     "firma",       "nowa faktura sprzedazowa"),
    Trasa("POST",   "/api/firma/faktury/{numer}/wplyw", "firma", "oznaczyc wplyw na konto"),
    Trasa("POST",   "/api/firma/koszty",      "firma",       "dodac koszt firmowy"),
    Trasa("POST",   "/api/firma/daniny/{klucz}/zaplacone", "firma", "oznaczyc danine jako zaplacona"),
    Trasa("POST",   "/api/majatek/aktywa",    "majatek",     "dodac aktywo"),
    Trasa("POST",   "/api/majatek/zobowiazania", "majatek",  "dodac zobowiazanie"),
    Trasa("POST",   "/api/godziny",           "godziny",     "dodac godziny"),
    Trasa("PUT",    "/api/kotwica",           "plynnosc",    "odczyt salda — ZRODLO kotwicy prognozy"),
    Trasa("POST",   "/api/ustawienia/kategorie", "ustawienia", "nowa kategoria"),
    Trasa("PUT",    "/api/ustawienia/kategorie/{id}", "ustawienia", "zmienic kategorie, w tym znacznik 'niezbedna'"),
    Trasa("POST",   "/api/ustawienia/stawki/{id}/zatwierdz", "ustawienia",
          "PODPIS DARKA pod stawka — jedyna droga z 'proponowana' do 'zatwierdzona'"),
    Trasa("POST",   "/api/ustawienia/import-arkusza", "ustawienia", "wgranie pliku arkusza"),
    Trasa("POST",   "/api/doradca/pytanie",   "doradca",     "pytanie wlasnymi slowami; model FORMULUJE, silnik liczy"),
)

WSZYSTKIE = ODCZYT + ZAPIS

#: Trasy, bez ktorych stara zakladka Budzet NIE MOZE zostac wylaczona.
WARUNEK_WYLACZENIA = tuple(t for t in WSZYSTKIE if t.warunek_wylaczenia)

assert len(WARUNEK_WYLACZENIA) == 5, (
    "P-1 wymienia CZTERY operacje: dodac wpis, wycofac wpis, ustawic pozycje "
    "planu, zakonczyc pozycje planu. Piata trasa to POST /api/plan — "
    "'ustawic' rozbija sie na dodanie i zmiane. Zmiana tej liczby wymaga "
    f"zmiany tego zdania, nie samej asercji. Jest: {len(WARUNEK_WYLACZENIA)}"
)


def tabela() -> str:
    """Blok do dokumentu. Dokument WOLA ten plik, nie przepisuje go."""
    w = ["| Metoda | Ścieżka | Ekran | Co robi |", "|---|---|---|---|"]
    for t in WSZYSTKIE:
        gwiazdka = " **(warunek wyłączenia)**" if t.warunek_wylaczenia else ""
        w.append(f"| `{t.metoda}` | `{t.sciezka}` | {t.ekran} | {t.co_robi}{gwiazdka} |")
    return "\n".join(w)


if __name__ == "__main__":
    print(f"tras łącznie: {len(WSZYSTKIE)} "
          f"({len(ODCZYT)} odczytu, {len(ZAPIS)} zapisu)")
    print(f"warunek wyłączenia starej zakładki: {len(WARUNEK_WYLACZENIA)} tras")
