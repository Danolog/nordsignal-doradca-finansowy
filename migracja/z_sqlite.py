# -*- coding: utf-8 -*-
"""PRZENIESIENIE DANYCH: SQLite poprzednika -> PostgreSQL.

STAN NA 2026-08-29 (W4): TEN MODUL NIE MA DZIS ZADANIA I TO JEST DECYZJA,
NIE PRZEOCZENIE. Darek rozstrzygnal (08:44 i 09:19), ze **aplikacja startuje
PUSTA od 1 IX 2026**: 204 wpisy i 46 pozycji planu poprzednika NIE MIGRUJA,
a jego baza zyje wylacznie jako dane robocze do budowy
(`~/Dane-robocze-doradca-finansowy/`, poza repozytorium). Baza produkcyjna
zostala postawiona pusta 2026-08-29 i taka ma zostac.

MODUL ZOSTAJE, bo opisuje TRZY ZAMIANY TYPOW, ktore i tak zaszly w schemacie,
i bo bramka odbioru (dwie rowne liczby) jest jedynym sensownym ksztaltem
kazdego przyszlego zaciagu danych — w tym miesiecznego zaciagu danych rynku.
**To JEDYNE miejsce w tym projekcie, ktore po W4 nadal importuje `sqlite3`**
— i importuje go jako czytnik CUDZEGO pliku, nie jako sterownik naszej bazy.
Straznik `testy/test_granice.py` pilnuje, zeby nie wrocil do `silnik/`.

JEDNORAZOWE. Uruchamiane raz, z kopia bazy zrodlowej zrobiona PRZED.

BRAMKA ODBIORU — DWIE LICZBY, KTORE MUSZA BYC ROWNE (PRD §6.5):
  1. licznosc: tabela po tabeli, ile wierszy wyszlo i ile weszlo;
  2. suma kontrolna kwot: suma wszystkich kwot po obu stronach.

"Przepisalem i wyglada dobrze" NIE JEST odbiorem. Kontrola licznosci istnieje,
bo sprawdzenie, do ktorego nic nie dociera, melduje sukces — pusty zbior
przechodzi kazda petle weryfikujaca.

TRZY ZAMIANY TYPOW, kazda moze cicho zepsuc dane:
  TEXT -> NUMERIC : napis "1305.05" musi trafic jako Decimal, nie przez float.
                    Przejscie przez float gubi grosze i NIE ZGLASZA bledu.
  TEXT -> DATE    : "2026-9-1" i "2026-09-01" to w SQLite dwa rozne napisy
                    i ten sam dzien. Po zamianie na DATE roznica znika —
                    ale przy okazji moze zniknac wiersz, ktorego nie da sie
                    odczytac. Taki wiersz ma PRZERWAC przenoszenie, nie zostac
                    pominietym.
  0/1  -> BOOLEAN : `NULL` znaczy "nie wiem" i ma zostac `NULL`, nie `FALSE`.

CO SIE DOPISUJE PO DRODZE:
  `wpisy_budzetu.zrodlo` — wszystkie 204 wiersze z 2025 dostaja
  'historia-2025' (decyzja Darka): widoczne w Raportach, NIEWIDOCZNE dla
  prognozy i rachunku podatkowego.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

#: Kolumny trzymajace kwoty — do sumy kontrolnej i do zamiany na Decimal.
KWOTY = {
    "wpisy_budzetu": ("kwota",),
    "plan_budzetu": ("kwota_planowana",),
    "przychody_jdg": ("kwota_netto", "kwota_vat"),
    "koszty_jdg": ("kwota_netto", "kwota_vat"),
    "majatek": ("wartosc",),
    "zobowiazania": ("kapital", "rata_minimalna"),
    "stan_konta": ("kwota",),
    "cele_oszczednosciowe": ("kwota_docelowa",),
}

#: Granica horyzontu danych (D-23). Wpisy wczesniejsze to HISTORIA.
GRANICA_HISTORII = "2026-09-01"


@dataclass(frozen=True)
class Kontrola:
    tabela: str
    wierszy_zrodlo: int
    wierszy_cel: int
    suma_zrodlo: Decimal
    suma_cel: Decimal

    @property
    def zgadza_sie(self) -> bool:
        return (self.wierszy_zrodlo == self.wierszy_cel
                and self.suma_zrodlo == self.suma_cel)

    def __str__(self) -> str:
        znak = "OK " if self.zgadza_sie else "BLAD"
        return (f"{znak} {self.tabela:22} "
                f"wierszy {self.wierszy_zrodlo} -> {self.wierszy_cel}   "
                f"suma {self.suma_zrodlo} -> {self.suma_cel}")


def zmierz_zrodlo(sciezka_sqlite: str) -> dict[str, tuple[int, Decimal]]:
    """Pomiar PRZED przeniesieniem. Bez niego nie ma z czym porownac."""
    polaczenie = sqlite3.connect(sciezka_sqlite)
    wynik: dict[str, tuple[int, Decimal]] = {}
    try:
        tabele = [w[0] for w in polaczenie.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for tabela in tabele:
            ile = polaczenie.execute(f'SELECT COUNT(*) FROM "{tabela}"').fetchone()[0]
            suma = Decimal("0")
            for kolumna in KWOTY.get(tabela, ()):
                for (wartosc,) in polaczenie.execute(
                        f'SELECT "{kolumna}" FROM "{tabela}"'):
                    if wartosc is not None:
                        # Przez napis, NIGDY przez float — inaczej grosze gina
                        # po cichu i suma kontrolna przestaje kontrolowac.
                        suma += Decimal(str(wartosc))
            wynik[tabela] = (ile, suma)
    finally:
        polaczenie.close()
    return wynik


def raport(zrodlo: dict[str, tuple[int, Decimal]],
           cel: dict[str, tuple[int, Decimal]]) -> tuple[list[Kontrola], bool]:
    """Zestawienie obu stron. Zwraca kontrole i werdykt.

    Tabela obecna po jednej stronie i nieobecna po drugiej JEST bledem,
    a nie pominieciem — inaczej przeniesienie polowy danych zameldowaloby
    sukces na tej polowie, ktora dotarla.
    """
    kontrole = []
    for tabela in sorted(set(zrodlo) | set(cel)):
        z_ile, z_suma = zrodlo.get(tabela, (0, Decimal("0")))
        c_ile, c_suma = cel.get(tabela, (0, Decimal("0")))
        kontrole.append(Kontrola(tabela, z_ile, c_ile, z_suma, c_suma))
    return kontrole, all(k.zgadza_sie for k in kontrole)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("uzycie: python migracja/z_sqlite.py <sciezka-do-bazy.db>")
        raise SystemExit(2)

    pomiar = zmierz_zrodlo(sys.argv[1])
    print("POMIAR ZRODLA (przed przeniesieniem):")
    for tabela, (ile, suma) in pomiar.items():
        print(f"  {tabela:22} {ile:>5} wierszy   suma kwot {suma}")
    print("\nPrzeniesienie do PostgreSQL: NIEZBUDOWANE.")
    print("Ten modul niesie dzis WYLACZNIE pomiar i bramke odbioru —")
    print("i to jest wlasciwa kolejnosc: bramka powstaje przed operacja,")
    print("nie po niej.")
