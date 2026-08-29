// DANE EKRANU PLYNNOSC — WOLANIE TRASY, nie stale.
//
// CZEGO TU NIE MA OD Z7: piatki sald odczytanych z rubryki ramki, trzech
// punktow odtworzonych z rysunku z bledem +/- 11 zl i szesciu pozycji ksiegi.
// Wszystko to przychodzi z `GET /api/plynnosc`, czyli z `rdzen/prognoza_plynnosci`.
// Blad odczytu z rysunku zniknal razem z rysunkiem — to jest cala korzysc
// z podpiecia i warto ja nazwac: liczby przestaly byc obrazem liczb.
// Pilnuje tego straznik `testy/test_dane_bez_kwot.py`.
//
// DRUGA TRASA — KOTWICA — JEST TU, A NIE OSOBNO. `PUT /api/kotwica` oddaje
// CALY ekran, a nie „zapisano": nowy odczyt stanu konta przesuwa punkt startu
// prognozy, wiec zmienia naraz werdykt, dzien pod kreska, saldo minimalne
// i cala serie. Odpowiedz „zapisano" kazalaby przegladarce albo zlozyc te
// liczby po swojemu (drugi nosnik), albo odpytac drugi raz (dwa przebiegi
// prognozy dla jednej chwili).

import type { DanePlynnosci, Data, Kwota } from "../kontrakt";
import { wywolaj } from "./warstwa-sieciowa";

export function pobierzPlynnosc(dzis?: string | null): Promise<DanePlynnosci> {
  return wywolaj<DanePlynnosci>("/api/plynnosc", { dzis });
}

/**
 * Odczyt stanu konta — ZRODLO kotwicy prognozy.
 *
 * KWOTA MOZE BYC UJEMNA i jest jedyna taka w tej aplikacji: konto na debecie
 * to realny stan konta, nie blad wpisu. Regula „minus jest w typie wpisu"
 * NIE OBOWIAZUJE tutaj — tam kierunek niesie typ pozycji, tu znak jest
 * czescia odczytu.
 */
export function zapiszKotwice(
  odczyt: { data: Data; kwota: Kwota },
  dzis?: string | null,
): Promise<DanePlynnosci> {
  return wywolaj<DanePlynnosci>("/api/kotwica", {
    metoda: "PUT",
    tresc: odczyt,
    dzis,
  });
}
