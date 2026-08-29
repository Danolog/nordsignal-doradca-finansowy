// DANE EKRANU BUDZET — WOLANIE SZESCIU TRAS, nie stale.
//
// ZERO KWOT W TYM PLIKU, tak samo jak w `ksiegowanie.ts` i `plynnosc.ts`.
// Kazda liczba przychodzi z `GET /api/budzet`, czyli z silnika, ktory jest
// JEDYNYM nosnikiem regul budzetu. Pilnuje tego `testy/test_dane_bez_kwot.py`.
//
// SZESC TRAS, SZESC FUNKCJI. Ekran nie sklada adresow i nie zna ksztaltu
// zadania — wola te funkcje. Spis tras: `api/trasy.py`, pozycje o ekranie
// „budzet"; kontrola licznosci po tamtej stronie: `testy/test_trasy_budzet.py`.
//
// TRASY KASUJACEJ PLAN TU NIE MA I NIE BEDZIE (Z-9). Kosz przy pozycji planu
// KONCZY REGULE od wskazanego miesiaca w przod — `zakonczPozycjePlanu` wola
// `POST /api/plan/{id}/zakoncz`, nigdy `DELETE`. Historia zostaje nietknieta:
// wczesniejsze miesiace nadal pokazuja, ze pozycja byla zaplanowana i ile
// z niej wykonano. `magazyn.usun_plan` istnieje w silniku i jest swiadomie
// odciety od warstwy sieciowej; pilnuje tego
// `testy/test_nosniki.py::test_kosz_planu_KONCZY_regule_a_nie_kasuje`.
//
// KAZDY ZAPIS ODDAJE CALY EKRAN — nie „zapisano". Jedna zmiana planu rusza
// NARAZ trzy kafelki, bilans, tabele „Plan kontra wykonanie", liste pozycji
// i licznik naglowka. Przegladarka, ktora doliczylaby je sobie sama, bylaby
// drugim nosnikiem kazdej z tych regul, a rozjazd bylo by widac dopiero po
// odswiezeniu strony. Nosnik tej decyzji stoi po drugiej stronie granicy:
// `silnik/ekran_budzet.py::OdpowiedzBudzetu`.
//
// KWOTA JEDZIE NAPISEM. Zero `Number()` i zero `parseFloat` na jej sciezce —
// u poprzednika taki krok gubil grosze i zwracal 200 (CLAUDE.md §3.1).

import type { DaneBudzetu, Kwota, TypWpisu } from "../kontrakt";
import { wywolaj } from "./warstwa-sieciowa";

/**
 * Odpowiedz kazdego z czterech zapisow tego ekranu.
 *
 * NIE JEST W `kontrakt.ts` SWIADOMIE — tak samo jak `OdpowiedzZapisu`
 * Ksiegowania. Tamten plik opisuje ksztalt EKRANU i ma po stronie Pythona
 * odpowiednik pilnowany strażnikiem `testy/test_kontrakt_dwa_nosniki.py`,
 * ktory wymaga TEGO SAMEGO zbioru ksztaltow po obu stronach. To jest ksztalt
 * WARSTWY SIECIOWEJ (`silnik/ekran_budzet.py::OdpowiedzBudzetu`), spoza
 * tamtej krotki — dopisany do kontraktu zaczerwienilby straznika o rozjezdzie,
 * ktorego nie ma.
 *
 * `wynik` niesie SLOWO OD MAGAZYNU, nie przeredagowane: „nowa" /
 * „zaktualizowana" / „zwersjonowana" przy ustawianiu, „skasowana" /
 * „zamknieta" / „pominieta" przy konczeniu. To jedyne miejsce, w ktorym
 * czlowiek dowiaduje sie, czy jego zmiana zalozyla nowa regule, czy zamknela
 * stara — a te dwie rzeczy inaczej wygladaja w historii.
 */
export type OdpowiedzBudzetu = {
  stan: "plan_ustawiony" | "plan_zakonczony" | "plan_skopiowany" | "cel_dodany";
  wynik: string;
  id: number | null;
  dane: DaneBudzetu;
};

/** Pozycja planu w ksztalcie, w jakim sklada ja panel — bez tozsamosci. */
export type PozycjaZEkranu = {
  typ: TypWpisu;
  kategoria: string;
  kwota: Kwota;
  opis: string;
  dzien: number | null;
  coIleMiesiecy: number;
};

export function pobierzBudzet(dzis?: string | null): Promise<DaneBudzetu> {
  return wywolaj<DaneBudzetu>("/api/budzet", { dzis });
}

/**
 * „Dodaj pozycje planu" — REGULA obowiazujaca od wskazanego miesiaca.
 *
 * Pozycja zalozona tutaj obowiazuje do odwolania i wlasnie dlatego jej kosz
 * nazywa sie „Zakoncz". Gdyby byla jednomiesieczna, konczyc nie byloby czego.
 */
export function dodajPozycjePlanu(
  pozycja: PozycjaZEkranu,
  { miesiac, dzis }: { miesiac: string; dzis?: string | null },
): Promise<OdpowiedzBudzetu> {
  return wywolaj<OdpowiedzBudzetu>("/api/plan", {
    metoda: "POST",
    tresc: { ...pozycja, miesiac },
    dzis,
  });
}

/**
 * „Zmien pozycje planu" — zmiana obowiazuje OD wskazanego miesiaca w przod.
 *
 * TOZSAMOSC POZYCJI (typ, kategoria, opis) BIERZE SIE Z WIERSZA W BAZIE, nie
 * z tego zadania — i dlatego nie ma jej w tresci. Zmiana kategorii ta droga
 * nie bylaby poprawka tej samej pozycji, tylko podmiana jednej na inna,
 * a wykonanie policzone juz w starej kategorii zostaloby przy niej.
 * Nosnik reguly: `silnik/ekran_budzet.py::zmien_pozycje`.
 */
export function zmienPozycjePlanu(
  id: number,
  zmiana: { kwota: Kwota; dzien: number | null; coIleMiesiecy: number },
  { miesiac, dzis }: { miesiac: string; dzis?: string | null },
): Promise<OdpowiedzBudzetu> {
  return wywolaj<OdpowiedzBudzetu>(`/api/plan/${id}`, {
    metoda: "PUT",
    tresc: { ...zmiana, miesiac },
    dzis,
  });
}

/**
 * „Zakoncz te pozycje od <miesiac>" — KONIEC REGULY, NIGDY KASOWANIE.
 *
 * Metoda jest `POST`, nie `DELETE`, i to nie jest kwestia gustu: `DELETE`
 * obiecywalby usuniecie, a tu nic sie nie usuwa. Wczesniejsze miesiace
 * zostaja bez zmian — zmienia sie wylacznie przyszlosc.
 *
 * `zakres` zostaje po stronie silnika (domyslnie „ten_i_nastepne"). Ekran ma
 * JEDNA kontrolke konca reguly, wiec podawanie zakresu stad byloby drugim
 * nosnikiem wartosci domyslnej.
 */
export function zakonczPozycjePlanu(
  id: number,
  { miesiac, dzis }: { miesiac: string; dzis?: string | null },
): Promise<OdpowiedzBudzetu> {
  return wywolaj<OdpowiedzBudzetu>(`/api/plan/${id}/zakoncz`, {
    metoda: "POST",
    tresc: { miesiac },
    dzis,
  });
}

/**
 * „Skopiuj z wrzesnia" — plan poprzedniego miesiaca na wskazany.
 *
 * `zMiesiaca` NIE JEDZIE stad. Zrodlo wyprowadza silnik tym samym nosnikiem,
 * ktorym sklada napis przycisku (`napisKopiujZ`); podane z przegladarki
 * byloby drugim nosnikiem tej samej reguly i rozjechaloby sie z napisem
 * na Nowym Roku.
 */
export function kopiujPlan(
  { miesiac, dzis }: { miesiac: string; dzis?: string | null },
): Promise<OdpowiedzBudzetu> {
  return wywolaj<OdpowiedzBudzetu>("/api/plan/kopiuj", {
    metoda: "POST",
    tresc: { miesiac },
    dzis,
  });
}

/**
 * „Usun zaznaczone" w Historii — WYCOFANIE WPISU, nie pozycji planu.
 *
 * DWA WYWOLANIA I TO JEST DECYZJA, NIE NIEDBALSTWO. Regula „zapis oddaje caly
 * ekran, wiec nie odpytuj drugi raz" dotyczy szesciu tras TEGO ekranu.
 * `DELETE /api/wpisy/{id}` nalezy do Ksiegowania i oddaje `DaneKsiegowania` —
 * czyli inny ekran. Zlozenie `DaneBudzetu` z tamtej odpowiedzi w przegladarce
 * byloby drugim nosnikiem calego rachunku planu; ponowny odczyt jest tanszy
 * i ma jedno zrodlo prawdy.
 *
 * PROG: gdy `DELETE /api/wpisy/{id}` zacznie oddawac ekran wolajacego (albo
 * powstanie osobna trasa wycofania po stronie Budzetu), drugie wywolanie
 * znika. Straznik: `testy/test_ekran_budzet.py::
 * test_wycofanie_wpisu_ODPYTUJE_BUDZET_bo_trasa_oddaje_inny_ekran`.
 */
export async function wycofajWpisZBudzetu(
  id: number,
  dzis?: string | null,
): Promise<DaneBudzetu> {
  await wywolaj<unknown>(`/api/wpisy/${id}`, { metoda: "DELETE", dzis });
  return pobierzBudzet(dzis);
}

/** „Dodaj cel" — cel oszczednosciowy z terminem. */
export function dodajCel(
  cel: { nazwa: string; kategoria: string; kwotaDocelowa: Kwota; termin: string },
  { miesiac, dzis }: { miesiac: string; dzis?: string | null },
): Promise<OdpowiedzBudzetu> {
  return wywolaj<OdpowiedzBudzetu>("/api/cele", {
    metoda: "POST",
    tresc: { ...cel, miesiac },
    dzis,
  });
}
