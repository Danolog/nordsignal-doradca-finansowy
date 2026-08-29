# -*- coding: utf-8 -*-
"""JEDYNY NOSNIK LICZB POCHODZACYCH Z PRAWA.

Zadna kwota ani stopa wynikajaca z ustawy, rozporzadzenia albo komunikatu ZUS
nie wystepuje w kodzie silnika. Silnik wola stad, a to, co tu stoi, ma przy
sobie podstawe prawna, date odczytu i podpis czlowieka, ktory to zatwierdzil.

DLACZEGO TO NIE JEST SLOWNIK W PLIKU. Poprzednia aplikacja trzymala stawki
jako stale w module (`rdzen/stawki.py`) — z zrodlami, ale bez okresu
obowiazywania i bez sposobu, zeby aplikacja sama zauwazyla, ze wartosc sie
zestarzala. Zmiana stawki wymagala zmiany kodu i wdrozenia. Tu jest tabela:
wartosc ma date od-do, a nowa wartosc dopisuje sie obok starej, nie zamiast
niej. Rachunek za wrzesien 2026 policzy sie stawka wrzesniowa takze wtedy,
gdy dzis mamy marzec 2027.

DWA STANY I JEDNA GRANICA MIEDZY NIMI.
  `zatwierdzona`  — silnik ja widzi i liczy nia kwoty;
  `proponowana`   — silnik jej NIE widzi; stoi w Ustawieniach jako propozycja
                    do zatwierdzenia, z pokazaniem "stara -> nowa -> zrodlo".
Automat (czujka aktow, kontrola GUS, odczyt stron) tworzy WYLACZNIE wiersze
`proponowana`. Nie ma drogi, ktora pozwolilaby maszynie wpisac stawke do
rachunku — i to jest cel, nie ostroznosc.

POWOD ZMIERZONY, NIE TEORETYCZNY. Rownolegla wersja tej aplikacji miala
czujke aktow prawnych, ktora PRZY AWARII API zwracala akty zmyslone,
nieodroznialne od prawdziwych. Automat wpisujacy stawke zamienia taka awarie
w zly przelew do urzedu.

JEDNOSTKA JEST POLEM, NIE UMOWA. W poprzedniej aplikacji dwie stopy
procentowe byly trzymane w dwoch roznych jednostkach (oprocentowanie
w procentach, stawka ryczaltu w ulamku), a rozroznienie zylo w komentarzu
w README. Pomnozenie kapitalu przez 9 zamiast przez 0,09 to blad stukrotny.
Tutaj jednostka jedzie razem z wartoscia i `wartosc_jako_ulamek` odmawia
zgadywania.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

#: Stany wiersza. `wycofana` sluzy sladowi: wartosc, ktora okazala sie bledna,
#: przestaje byc liczona, ale nie znika — inaczej nie da sie odtworzyc, czym
#: policzono kwote sprzed pol roku.
STANY = ("zatwierdzona", "proponowana", "wycofana")

#: Jednostki. `zl` — kwota w zlotych; `ulamek` — 0,09 znaczy 9%;
#: `procent` — 9 znaczy 9%. Trzecia istnieje, bo tak czlowiek wpisuje stope
#: w formularzu i tlumaczenie w glowie jest miejscem na pomylke.
JEDNOSTKI = ("zl", "ulamek", "procent")

SCHEMAT = """
CREATE TABLE IF NOT EXISTS rejestr_stawek (
    id                  BIGSERIAL PRIMARY KEY,
    klucz               TEXT        NOT NULL,
    wartosc             NUMERIC(16,6) NOT NULL,
    jednostka           TEXT        NOT NULL,
    obowiazuje_od       DATE        NOT NULL,
    obowiazuje_do       DATE,
    podstawa_prawna     TEXT,
    zrodlo_url          TEXT        NOT NULL,
    data_odczytu        DATE        NOT NULL,
    status              TEXT        NOT NULL,
    zatwierdzil         TEXT,
    data_zatwierdzenia  DATE,
    niezweryfikowane    TEXT,
    opis                TEXT        NOT NULL DEFAULT '',
    CONSTRAINT stan_znany     CHECK (status IN ('zatwierdzona','proponowana','wycofana')),
    CONSTRAINT jednostka_znana CHECK (jednostka IN ('zl','ulamek','procent')),
    CONSTRAINT okres_sensowny CHECK (obowiazuje_do IS NULL OR obowiazuje_do >= obowiazuje_od),
    -- Zatwierdzona bez podpisu jest sprzecznoscia: status ma znaczyc
    -- "czlowiek to potwierdzil", a nie "ktos ustawil pole".
    CONSTRAINT zatwierdzona_ma_podpis CHECK (
        status <> 'zatwierdzona'
        OR (zatwierdzil IS NOT NULL AND data_zatwierdzenia IS NOT NULL)
    )
);

-- Dwie zatwierdzone wartosci tego samego klucza na ten sam dzien to nie jest
-- konflikt do rozstrzygniecia w kodzie — to jest blad danych. Baza go nie
-- wpusci, wiec `obowiazujaca` nigdy nie musi wybierac miedzy dwiema prawdami.
CREATE UNIQUE INDEX IF NOT EXISTS rejestr_stawek_jedna_obowiazujaca
    ON rejestr_stawek (klucz, obowiazuje_od)
    WHERE status = 'zatwierdzona';
"""


@dataclass(frozen=True)
class Stawka:
    """Jedna wartosc z prawa, razem z metryka pochodzenia."""

    klucz: str
    wartosc: Decimal
    jednostka: str
    obowiazuje_od: date
    obowiazuje_do: date | None
    zrodlo_url: str
    data_odczytu: date
    status: str
    podstawa_prawna: str | None = None
    zatwierdzil: str | None = None
    data_zatwierdzenia: date | None = None
    niezweryfikowane: str | None = None
    opis: str = ""

    def __post_init__(self) -> None:
        if self.jednostka not in JEDNOSTKI:
            raise ValueError(f"nieznana jednostka: {self.jednostka!r}")
        if self.status not in STANY:
            raise ValueError(f"nieznany stan: {self.status!r}")
        if self.status == "zatwierdzona" and not self.zatwierdzil:
            raise ValueError(
                f"{self.klucz}: stawka zatwierdzona musi miec podpis — "
                "status ma znaczyc 'czlowiek to potwierdzil'"
            )

    def obowiazuje(self, dzien: date) -> bool:
        if dzien < self.obowiazuje_od:
            return False
        return self.obowiazuje_do is None or dzien <= self.obowiazuje_do

    @property
    def wartosc_jako_ulamek(self) -> Decimal:
        """Stopa jako ulamek — jedyna droga do pomnozenia przez kapital.

        ODMAWIA dla jednostki `zl`, zamiast zwrocic cos prawdopodobnego.
        Kwota w zlotych pomnozona przez kapital nie znaczy nic, a wynik
        wygladalby jak liczba.
        """
        if self.jednostka == "ulamek":
            return self.wartosc
        if self.jednostka == "procent":
            return self.wartosc / Decimal(100)
        raise ValueError(
            f"{self.klucz}: jednostka 'zl' nie jest stopa — "
            "nie ma czego zamienic na ulamek"
        )


class BrakStawki(LookupError):
    """Podnoszona zamiast zwrocenia wartosci domyslnej.

    DLACZEGO WYJATEK, A NIE `None` ALBO ZERO. Brak stawki to stan, w ktorym
    aplikacja NIE WIE, ile wynosi skladka — a zero i wartosc domyslna
    wygladaja na ekranie jak wiedza. Poprzednia aplikacja miala dokladnie
    ten wzorzec: stawka ryczaltu jako wartosc domyslna w trzech miejscach
    sprawiala, ze kazde wywolanie bez jawnej formy liczylo zle i milczalo.
    """


def obowiazujaca(stawki: list[Stawka], klucz: str, dzien: date) -> Stawka:
    """Jedyna droga silnika do wartosci z prawa.

    Bierze pod uwage WYLACZNIE wiersze `zatwierdzona`. Propozycja automatu
    nie wchodzi do zadnej kwoty, choc jest widoczna w Ustawieniach.
    """
    pasujace = [
        s for s in stawki
        if s.klucz == klucz and s.status == "zatwierdzona" and s.obowiazuje(dzien)
    ]
    if not pasujace:
        proponowane = sum(
            1 for s in stawki if s.klucz == klucz and s.status == "proponowana"
        )
        ogon = (
            f" Sa {proponowane} propozycje do zatwierdzenia w Ustawieniach."
            if proponowane else ""
        )
        raise BrakStawki(
            f"brak zatwierdzonej stawki {klucz!r} obowiazujacej {dzien}.{ogon}"
        )
    # Najpozniejszy poczatek obowiazywania. Indeks bazy nie dopusci dwoch
    # zatwierdzonych o tym samym `obowiazuje_od`, wiec wybor jest jednoznaczny.
    return max(pasujace, key=lambda s: s.obowiazuje_od)
