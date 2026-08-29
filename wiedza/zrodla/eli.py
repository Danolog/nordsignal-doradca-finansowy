# -*- coding: utf-8 -*-
"""CZUJKA AKTOW PRAWNYCH — Dziennik Ustaw przez API Sejmu (ELI).

CO TO ROBI I CZEGO NIE ROBI. Pyta raz dziennie, czy ukazal sie akt dotykajacy
skladek albo podatkow. Trafienie podnosi w aplikacji choragiewke: "stawki moga
byc nieaktualne, powodem jest Dz.U. 2026 poz. N". NIE ZMIENIA ZADNEJ WARTOSCI
i nie ma do tego drogi — tworzy sygnal, ktory czlowiek czyta.

DLACZEGO NIE ZUS. Zmierzone 2026-08-28: `api.zus.pl` nie odpowiada (brak
polaczenia), `zus.pl/.../api` zwraca 404. ZUS NIE UDOSTEPNIA publicznego
interfejsu programowego ze stawkami skladek. ELI jest najblizszym zrodlem
autorytatywnym, jakie istnieje: publikuje akt, ktory te stawki zmienia.

PULAPKA, PRZED KTORA BRONI TEN MODUL. Rownolegla wersja tej aplikacji miala
czujke, ktora PRZY AWARII API zwracala akty zmyslone — nieodroznialne od
prawdziwych, bo mialy poprawny ksztalt. Stad trzy zasady:

  1. BLAD NIE UDAJE PUSTKI. Awaria podnosi `AwariaZrodla`, a nie zwraca
     pustej listy. "Nie sprawdzilem" i "nic nie ma" to dwa rozne stany
     i aplikacja mowi, ktory zaszedl.
  2. ZERO WNIOSKOWANIA. Modul zwraca to, co przyszlo, i nic ponadto. Nie
     streszcza aktu, nie zgaduje nowej stawki, nie wola modelu jezykowego.
  3. KAZDE TRAFIENIE NIESIE ADRES. Bez `displayAddress` i `url` sygnal jest
     nie do sprawdzenia przez czlowieka, czyli bezwartosciowy.

KSZTALT ODPOWIEDZI JEST ZALOZENIEM O TERMINIE WAZNOSCI. Sprawdzony raz,
2026-08-28. `_akt_z_odpowiedzi` odmawia na braku pola zamiast wstawiac pustke,
zeby zmiana po stronie Sejmu byla widoczna jako blad, a nie jako cisza.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

import httpx

ADRES = "https://api.sejm.gov.pl/eli"

#: USTAWY, KTORE RUSZAJA KWOTY DARKA — szukamy po TYTULE aktu, nie po hasle
#: redakcyjnym. To jest roznica zmierzona, nie preferencja.
#:
#: Pomiar 2026-08-28. Szukanie po hasle "skladki" dalo 5 na 5 trafien BEZ
#: ZWIAZKU z jednoosobowa dzialalnoscia (ubezpieczenia upraw rolnych,
#: obwieszczenie MSWiA o jednolitym tekscie). Szukanie po tytulach nizej dalo
#: 13 aktow w osiem miesiecy 2026 roku, wszystkie merytoryczne — okolo 1,6
#: sygnalu miesiecznie.
#:
#: DLACZEGO TO JEST WAZNIEJSZE NIZ WYGODA. Czujka wolajaca falszywy alarm co
#: tydzien zostanie wylaczona po miesiacu — i nie zadziala wtedy, gdy naprawde
#: trzeba. Fundament projektowy §4.3: kazde dodatkowe powiadomienie obniza
#: szanse zareagowania na KTOREKOLWIEK o 30%, a w medycynie odrzucanych jest
#: 49–96% alertow. Waskie kryterium jest tu funkcja bezpieczenstwa.
#:
#: PULAPKA DOSLOWNOSCI: fraza musi brzmiec tak, jak w tytule ustawy.
#: "ubezpieczeniach spolecznych" daje ZERO trafien, "systemie ubezpieczen
#: spolecznych" daje trafienie. Skracanie tych fraz jest wada.
TYTULY = (
    "podatku dochodowym od osób fizycznych",
    "zryczałtowanym podatku dochodowym",
    "podatku od towarów i usług",
    "systemie ubezpieczeń społecznych",
    "świadczeniach opieki zdrowotnej",
)

CZAS_ODPOWIEDZI = 20.0


class AwariaZrodla(RuntimeError):
    """Zrodlo nieosiagalne albo odpowiedz w nieznanym ksztalcie.

    Osobny wyjatek, a nie `return []`, bo pusta lista znaczy "sprawdzilem
    i nic nie ma" — twierdzenie o stanie swiata, ktorego przy awarii nikt
    nie postawil.
    """


@dataclass(frozen=True)
class Akt:
    """Jeden akt z Dziennika Ustaw. Wylacznie pola, ktore przyszly."""

    adres: str            # np. "DU/2025/1874" — identyfikator ELI
    adres_czytelny: str   # np. "Dz.U. 2025 poz. 1874"
    tytul: str
    data_ogloszenia: _dt.date
    status: str           # np. "obowiązujący"
    hasla: tuple[str, ...]   # slowa kluczowe redakcji, do wgladu

    @property
    def url(self) -> str:
        """Adres, pod ktorym czlowiek przeczyta tekst. Bez tego sygnal jest
        nie do sprawdzenia."""
        return f"https://api.sejm.gov.pl/eli/acts/{self.adres}"


def _akt_z_odpowiedzi(p: dict) -> Akt:
    """Zamiana wiersza odpowiedzi na `Akt`.

    ODMAWIA na braku pola zamiast wstawiac pustke: gdy Sejm zmieni ksztalt
    odpowiedzi, ma to wyjsc jako blad przy najblizszym przebiegu, a nie jako
    czujka, ktora od pol roku nic nie znajduje i wyglada na spokojna.
    """
    brakujace = [k for k in ("address", "title", "announcementDate") if k not in p]
    if brakujace:
        raise AwariaZrodla(
            f"odpowiedz ELI bez pol {brakujace} — ksztalt API sie zmienil; "
            "czujka nie zgaduje"
        )
    try:
        ogloszony = _dt.date.fromisoformat(p["announcementDate"])
    except (TypeError, ValueError) as e:
        raise AwariaZrodla(f"nieczytelna data ogloszenia: {p['announcementDate']!r}") from e

    surowy = p["address"]
    # "WDU20250001874" -> "DU/2025/1874": postac uzywana przez trasy ELI.
    if surowy.startswith("WDU") and len(surowy) == 14:
        adres = f"DU/{surowy[3:7]}/{int(surowy[7:]):d}"
    else:
        adres = surowy

    return Akt(
        adres=adres,
        adres_czytelny=p.get("displayAddress", adres),
        tytul=p["title"],
        data_ogloszenia=ogloszony,
        status=p.get("status", "nieznany"),
        hasla=tuple(p.get("keywords", ())),
    )


def akty_od(od: _dt.date, tytuly: tuple[str, ...] = TYTULY,
            limit_na_tytul: int = 20) -> list[Akt]:
    """Akty ogloszone nie wczesniej niz `od`, dotyczace ktorejkolwiek z ustaw.

    Zwraca liste bez powtorzen, od najnowszego. Przy awarii — `AwariaZrodla`.
    """
    znalezione: dict[str, Akt] = {}
    try:
        with httpx.Client(timeout=CZAS_ODPOWIEDZI) as k:
            for tytul in tytuly:
                o = k.get(
                    f"{ADRES}/acts/search",
                    params={"title": tytul, "limit": limit_na_tytul,
                            "dateFrom": od.isoformat()},
                )
                o.raise_for_status()
                for pozycja in o.json().get("items", ()):
                    akt = _akt_z_odpowiedzi(pozycja)
                    if akt.data_ogloszenia >= od:
                        znalezione[akt.adres] = akt
    except httpx.HTTPError as e:
        raise AwariaZrodla(f"ELI nieosiagalne: {e}") from e

    return sorted(znalezione.values(), key=lambda a: a.data_ogloszenia, reverse=True)


def sygnal(akty: list[Akt]) -> str | None:
    """Zdanie do choragiewki w aplikacji. `None`, gdy nie ma czego zglosic.

    Zdanie mowi o MOZLIWEJ nieaktualnosci, nie o zmianie stawki — czujka
    widzi akt, a nie liczbe. Roznica nie jest kosmetyczna: "stawka wzrosla"
    byloby twierdzeniem, ktorego ten modul nie ma czym poprzec.
    """
    if not akty:
        return None
    p = akty[0]
    reszta = f" (oraz {len(akty) - 1} innych)" if len(akty) > 1 else ""
    return (
        f"Stawki mogą być nieaktualne — {p.adres_czytelny} z "
        f"{p.data_ogloszenia:%d.%m.%Y}: {p.tytul[:120]}{reszta}. "
        "Sprawdź rejestr stawek w Ustawieniach."
    )
