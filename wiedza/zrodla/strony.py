# -*- coding: utf-8 -*-
"""ODCZYT STAWEK ZE STRON ZUS I biznes.gov.pl.

DLACZEGO ODCZYT STRONY, A NIE API. Zmierzone 2026-08-28: `api.zus.pl` nie
odpowiada, `zus.pl/.../api` zwraca 404. ZUS NIE UDOSTEPNIA publicznego
interfejsu programowego ze stawkami skladek. Strona jest jedynym miejscem,
w ktorym te liczby stoja — wiec czytamy strone, ale czytamy ja ostroznie.

TRZY ZASADY, KAZDA ZAMYKA KONKRETNA AWARIE:

  1. KOTWICA NA FRAZIE, NIE NA POZYCJI. Regula szuka "na ubezpieczenie
     emerytalne - 19,52% podstawy", a nie "trzecia liczba na stronie".
     Przestawienie akapitu przez redakcje ZUS nie ma prawa podmienic stopy
     emerytalnej na rentowa.

  2. BRAK TRAFIENIA TO BLAD, NIE ZGODA. Regula, ktora nic nie znalazla,
     podnosi `NieUmiemOdczytac`. Zwrocenie "brak zmian" byloby sprawdzeniem,
     do ktorego nic nie dociera — a takie sprawdzenie MELDUJE SUKCES.
     To jest ta sama klasa awarii co pusty zbior w petli weryfikujacej.

  3. ZERO ZAPISU. Modul zwraca ROZJAZDY. Nie tworzy wartosci obowiazujacej,
     nie dotyka rejestru, nie ma do tego drogi. Propozycje zatwierdza czlowiek.

CO SIE STANIE, GDY ZUS PRZEBUDUJE STRONE: `NieUmiemOdczytac` z nazwa reguly.
Aplikacja liczy dalej z zatwierdzonych stawek i mowi "nie udalo sie sprawdzic
od N dni". Awaria do stanu uzytecznego, nie do zera i nie do ciszy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx

CZAS_ODPOWIEDZI = 25.0
NAGLOWKI = {"User-Agent": "Mozilla/5.0 (Macintosh) DoradcaFinansowy/0.1"}

#: Liczba po polsku: przecinek dziesietny, spacja jako separator tysiecy
#: (takze spacja niełamliwa, ktorej strony uzywaja czesciej niz zwyklej).
#: PULAPKA ZLAPANA POMIAREM (2026-08-29). Pierwsza wersja miala gwiazdke
#: przy grupie tysiecy. Na napisie "5652 zl" dopasowala "565" i sie
#: zatrzymala, bo "2" nie zaczyna trojki cyfr — odczyt dawal podstawe
#: skladek DZIESIECIOKROTNIE ZA NISKA i wygladal poprawnie. Naprawa:
#: forma z separatorem wymaga CO NAJMNIEJ JEDNEJ grupy tysiecy (`+`),
#: wiec liczba bez separatora spada do galezi `\d+` i jest czytana
#: w calosci. Straznik: testy/test_odczyt_stron.py.
LICZBA = r"(\d{1,3}(?:[\s ]\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)"


class NieUmiemOdczytac(RuntimeError):
    """Regula nie trafila. Osobny wyjatek, bo cisza wyglada jak zgoda."""


class AwariaZrodla(RuntimeError):
    """Strona nieosiagalna."""


@dataclass(frozen=True)
class Regula:
    """Jak wyjac jedna liczbe ze strony.

    `klucz`     — klucz w rejestrze stawek;
    `wzorzec`   — wyrazenie z DOKLADNIE jedna grupa, kotwiczone na frazie;
    `jednostka` — jednostka odczytanej wartosci ('zl' / 'procent').
    """
    klucz: str
    wzorzec: str
    jednostka: str
    opis: str


#: Reguly sprawdzone na biznes.gov.pl/pl/portal/00274, odczyt 2026-08-29.
#: Fraza cytowana ze strony, nie wymyslona: "na ubezpieczenie emerytalne
#: – 19,52% podstawy". Myslnik na stronie jest PODLUZNY (–), nie zwykly.
SKLADKI = (
    Regula("zus.podstawa_spolecznych",
           r"podstawa,?\s+od\s+której\s+liczy\s+się\s+składki[^.]{0,60}?wynosi\s*" + LICZBA + r"\s*zł",
           "zl", "Minimalna podstawa wymiaru składek społecznych, duży ZUS."),
    Regula("zus.emerytalna",
           r"ubezpieczenie\s+emerytalne\s*[–—-]\s*" + LICZBA + r"\s*%",
           "procent", "Stopa składki emerytalnej."),
    Regula("zus.rentowa",
           r"ubezpieczenia\s+rentowe\s*[–—-]\s*" + LICZBA + r"\s*%",
           "procent", "Stopa składki rentowej."),
    Regula("zus.chorobowa",
           r"ubezpieczenie\s+chorobowe\s*[–—-]\s*" + LICZBA + r"\s*%",
           "procent", "Stopa składki chorobowej."),
)


@dataclass(frozen=True)
class Rozjazd:
    klucz: str
    w_rejestrze: Decimal | None
    na_stronie: Decimal
    jednostka: str
    zrodlo_url: str

    def zdanie(self) -> str:
        if self.w_rejestrze is None:
            return (f"{self.klucz}: brak w rejestrze, na stronie "
                    f"{self.na_stronie} ({self.jednostka}).")
        return (f"{self.klucz}: rejestr ma {self.w_rejestrze}, strona podaje "
                f"{self.na_stronie} ({self.jednostka}).")


def _tekst(url: str) -> str:
    try:
        with httpx.Client(timeout=CZAS_ODPOWIEDZI, follow_redirects=True,
                          headers=NAGLOWKI) as k:
            o = k.get(url)
            o.raise_for_status()
    except httpx.HTTPError as e:
        raise AwariaZrodla(f"{url} nieosiagalne: {e}") from e
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", o.text, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[\s ]+", " ", t)


def _na_decimal(napis: str) -> Decimal:
    czysty = napis.replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(czysty)
    except InvalidOperation as e:
        raise NieUmiemOdczytac(f"nieczytelna liczba: {napis!r}") from e


def odczytaj(url: str, reguly=SKLADKI) -> dict[str, tuple[Decimal, str]]:
    """Wartosci ze strony. KAZDA regula musi trafic — inaczej blad.

    Zwrocenie czesci wynikow byloby gorsze niz blad: brakujaca pozycja
    wygladalaby jak "ta stawka sie nie zmienila".
    """
    tekst = _tekst(url)
    wynik: dict[str, tuple[Decimal, str]] = {}
    nietrafione: list[str] = []
    for r in reguly:
        m = re.search(r.wzorzec, tekst, re.IGNORECASE)
        if not m:
            nietrafione.append(r.klucz)
            continue
        wynik[r.klucz] = (_na_decimal(m.group(1)), r.jednostka)
    if nietrafione:
        raise NieUmiemOdczytac(
            f"{url}: reguly bez trafienia {nietrafione}. Strona zmienila "
            "uklad albo tresc — czytanie NIE JEST kontynuowane, bo czesciowy "
            "wynik wyglada jak 'reszta bez zmian'."
        )
    return wynik


def porownaj(stawki, odczytane: dict[str, tuple[Decimal, str]],
             url: str) -> list[Rozjazd]:
    """Zestawienie rejestru ze strona. ZERO ZAPISU — zwraca rozjazdy.

    Porownanie idzie po ULAMKU, zeby stopa zapisana w rejestrze jako 0,1952
    i na stronie jako 19,52% wyszla jako TA SAMA wartosc. To jest miejsce,
    w ktorym pulapka jednostek zabilaby cala kontrole: bez zamiany kazde
    porownanie zglaszaloby rozjazd stukrotny.
    """
    from wiedza.rejestr import Stawka

    biezace = {s.klucz: s for s in stawki if s.status == "zatwierdzona"}
    rozjazdy: list[Rozjazd] = []

    for klucz, (wartosc, jednostka) in odczytane.items():
        s = biezace.get(klucz)
        ze_strony = Stawka(
            klucz=klucz, wartosc=wartosc, jednostka=jednostka,
            obowiazuje_od=(s.obowiazuje_od if s else __import__("datetime").date.today()),
            obowiazuje_do=None, zrodlo_url=url,
            data_odczytu=__import__("datetime").date.today(), status="proponowana",
        )
        if s is None:
            rozjazdy.append(Rozjazd(klucz, None, wartosc, jednostka, url))
            continue
        if jednostka == "zl":
            zgodne = s.wartosc == wartosc
        else:
            zgodne = s.wartosc_jako_ulamek == ze_strony.wartosc_jako_ulamek
        if not zgodne:
            rozjazdy.append(Rozjazd(klucz, s.wartosc, wartosc, jednostka, url))
    return rozjazdy
