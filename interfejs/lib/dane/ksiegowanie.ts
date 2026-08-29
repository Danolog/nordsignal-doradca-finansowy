// DANE EKRANU KSIEGOWANIE — WOLANIE TRAS, nie stale.
//
// CZEGO TU NIE MA OD Z7: ani jednej kwoty, ani jednej nazwy kategorii, ani
// jednego zdania o kolejnosci. Wszystko to przychodzi z `GET /api/ksiegowanie`,
// czyli z silnika, ktory jest JEDYNYM nosnikiem tych regul. Do Z6 stal tu stan
// pokazowy przepisany z ramki — mial jawny prog wymiany („przy podpieciu tras
// ten plik znika") i wlasnie ten prog zostal przekroczony.
// Pilnuje tego straznik `testy/test_dane_bez_kwot.py`.
//
// CZTERY TRASY, CZTERY FUNKCJE. Ekran nie sklada adresow i nie zna ksztaltu
// zadania — wola te funkcje. Gdyby skladal je sam, kazdy nowy ekran dokladalby
// wlasny nosnik tego samego wywolania.
//
// PO ZAPISIE ODSWIEZONY EKRAN PRZYCHODZI W ODPOWIEDZI, nie drugim zapytaniem.
// `silnik/ekran_ksiegowanie.py::OdpowiedzZapisu` niesie `dane` w komplecie,
// bo po zapisie zmieniaja sie NARAZ trzy rzeczy: licznik wpisow, lista
// ostatnich wpisow i kolejnosc kafelkow. Ekran, ktory dolicza je sobie sam,
// jest drugim nosnikiem kazdej z tych regul.

import type {
  DaneKsiegowania,
  PodgladSkutku,
  TypWpisu,
  Kwota,
  Data,
} from "../kontrakt";
import { wywolaj } from "./warstwa-sieciowa";

/**
 * Odpowiedz zapisu albo wycofania.
 *
 * NIE JEST W `kontrakt.ts` SWIADOMIE. Tamten plik opisuje ksztalt EKRANU
 * i ma po stronie Pythona odpowiednik pilnowany strażnikiem
 * `testy/test_kontrakt_dwa_nosniki.py`, ktory wymaga TEGO SAMEGO zbioru
 * ksztaltow po obu stronach. To jest ksztalt WARSTWY SIECIOWEJ
 * (`silnik/ekran_ksiegowanie.py::OdpowiedzZapisu`), spoza tamtej krotki —
 * dopisany do kontraktu zaczerwienilby straznika o rozjezdzie, ktorego nie ma.
 *
 * `stan` rozstrzyga, czy cokolwiek trafilo do bazy — nie kod odpowiedzi.
 * Kwota ujemna to nie blad zadania, tylko PYTANIE (przypadek (d) z §41.5).
 */
export type OdpowiedzZapisu = {
  stan: "zapisany" | "pytanie_o_minus" | "wycofany";
  id: number | null;
  kwota: Kwota | null;
  typ: TypWpisu | null;
  dane: DaneKsiegowania;
};

export type WpisZEkranu = {
  data: Data;
  typ: TypWpisu;
  kategoria: string;
  kwota: Kwota;
  szczegoly: string;
};

export function pobierzKsiegowanie(dzis?: string | null): Promise<DaneKsiegowania> {
  return wywolaj<DaneKsiegowania>("/api/ksiegowanie", { dzis });
}

export function zapiszWpis(
  wpis: WpisZEkranu,
  { dzis, potwierdzone = false }: { dzis?: string | null; potwierdzone?: boolean } = {},
): Promise<OdpowiedzZapisu> {
  return wywolaj<OdpowiedzZapisu>("/api/wpisy", {
    metoda: "POST",
    tresc: { ...wpis, potwierdzone },
    dzis,
  });
}

export function wycofajWpis(id: number, dzis?: string | null): Promise<OdpowiedzZapisu> {
  return wywolaj<OdpowiedzZapisu>(`/api/wpisy/${id}`, { metoda: "DELETE", dzis });
}

/**
 * „Co ruszy ten wpis" dla kwoty, ktorej jeszcze nie ma w bazie.
 *
 * DLACZEGO TO IDZIE DO SILNIKA, A NIE LICZY SIE NA EKRANIE. Karta obiecuje
 * cztery liczby: wykonanie typu, wykonanie kategorii, procent planu i zdanie
 * o tym, co sie NIE ruszylo. Kazda z nich jest wynikiem reguly budzetu.
 * Policzone w przegladarce bylyby drugim nosnikiem tych regul i rozjechalyby
 * sie z zapisem przy pierwszej zmianie — podglad obiecywalby jeden skutek,
 * a zapis dawal inny.
 */
export function pobierzPodglad(zapytanie: {
  data: Data;
  typ: TypWpisu;
  kategoria: string;
  kwota: Kwota;
}): Promise<PodgladSkutku> {
  return wywolaj<PodgladSkutku>("/api/wpisy/podglad", {
    metoda: "POST",
    tresc: zapytanie,
  });
}
