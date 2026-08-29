// DANE EKRANU PLYNNOSC — otypowane kontraktem, liczby z ramki `Main.dc.html`.
//
// PROG WYMIANY, JAWNY: przy podpieciu tras (Z6/Z7) ten plik znika, a jego
// miejsce zajmuje odpowiedz `GET /api/plynnosc`, ktora niesie serie
// `rdzen/prognoza_plynnosci.py`.
//
// SKAD SIE BIORA LICZBY — i gdzie konczy sie ich dokladnosc.
// Piec sald jest ODCZYTANYCH WPROST z rubryki ramki i jest dokladne co do
// grosza: 9 601,03 · 8 295,98 · 8 145,98 · 3 025,33 · −210,67.
// Trzy dalsze punkty serii (30 IX, 1 X, 13 X) NIE STOJA w rubryce — ramka
// niesie je wylacznie jako WSPOLRZEDNE rysunku, z dokladnoscia 0,1 px.
// Odtworzone przez odwrocenie skali wykresu; **blad odczytu +/- 11 zl**
// (0,05 px na 44 px wysokosci przy rozpietosci 9 811,70 zl).
// To jest granica pomiaru, nie zaokraglenie — i dlatego stoi tu napisana,
// zamiast udawac, ze te trzy liczby sa tej samej klasy co pozostale piec.

import type { DanePlynnosci, PozycjaKsiegi, PunktWykresu } from "../kontrakt";
import { OSTATNIE_SPRAWDZENIE } from "./powloka";

// Ksiega: piec dni, szesc pozycji. Saldo bite RAZ NA DZIEN.
// `saldoPoDniu: null` dla 25 IX w OBU wierszach — saldo tego dnia jest
// najnizszym punktem prognozy i stoi ponizej jako wiersz zamkniecia.
// Powtorzone w rubryce bylo by ta sama liczba dwa razy, a druga wygladalaby
// na blad rachunku.
const KSIEGA: readonly PozycjaKsiegi[] = [
  {
    dzien: "2026-09-02",
    pozycja: "Stan na dziś",
    // Spacje nierozdzielajace (U+00A0) w kwocie i w dacie — doslownie jak
    // w ramce. Kwota rozerwana miedzy wierszami przestaje byc kwota.
    dopisek: "— z odczytu 9 920,79 zł z 1 września",
    kwota: null,
    saldoPoDniu: "9601.03",
  },
  { dzien: "2026-09-12", pozycja: "Kredyt Revolut",     kwota: "-1305.05", saldoPoDniu: "8295.98" },
  { dzien: "2026-09-15", pozycja: "PGNiG",              kwota: "-150.00",  saldoPoDniu: "8145.98" },
  { dzien: "2026-09-21", pozycja: "ZUS",                kwota: "-5120.65", saldoPoDniu: "3025.33" },
  { dzien: "2026-09-25", pozycja: "Czesne WSB Merito",  kwota: "-660.00",  saldoPoDniu: null },
  { dzien: "2026-09-25", pozycja: "VAT",                kwota: "-2576.00", saldoPoDniu: null },
];

// Seria dzienna, 2 IX – 17 X (46 dni). Kazdy dzien ma wlasny punkt, bo linia
// laczaca tylko dni z pozycjami klamalaby o ksztalcie miedzy nimi.
function serie(od: string, ile: number, saldo: string): PunktWykresu[] {
  const [rok, miesiac, dzien] = od.split("-").map(Number);
  return Array.from({ length: ile }, (_, i) => {
    const d = new Date(Date.UTC(rok, miesiac - 1, dzien + i));
    return { dzien: d.toISOString().slice(0, 10), saldo };
  });
}

const WYKRES: readonly PunktWykresu[] = [
  ...serie("2026-09-02", 10, "9601.03"),   // 2–11 IX
  ...serie("2026-09-12", 3, "8295.98"),    // 12–14 IX
  ...serie("2026-09-15", 6, "8145.98"),    // 15–20 IX
  ...serie("2026-09-21", 4, "3025.33"),    // 21–24 IX
  ...serie("2026-09-25", 5, "-210.67"),    // 25–29 IX — pod kreską
  ...serie("2026-09-30", 1, "8196.26"),    // 30 IX   — odczyt z rysunku, ±11 zł
  ...serie("2026-10-01", 11, "7861.84"),   // 1–11 X  — odczyt z rysunku, ±11 zł
  ...serie("2026-10-12", 6, "6568.68"),    // 12–17 X — odczyt z rysunku, ±11 zł
];

export const DANE: DanePlynnosci = {
  odczyt: "2026-10-06",
  okresNapis: "wrzesień 2026 · 45 dni naprzód",
  ksiega: KSIEGA,
  wykres: WYKRES,
  dzienPodKreska: "2026-09-25",
  saldoMinimalne: "-210.67",
  dataSaldaMinimalnego: "2026-09-25",
  // Zdanie nazywa PRZYCZYNE, nie tylko fakt. Bez przyczyny liczba zostawia
  // lek bez wyjscia — a wzorzec zlej wiadomosci brzmi: liczba, zdanie,
  // dzialanie.
  zdanieWerdyktu:
    "25 września schodzisz poniżej zera — tego dnia wychodzi VAT i czesne.",
  horyzontDni: 23,
  liczbaPozycjiCoMnieCzeka: 7,
  koniecOknaCoMnieCzeka: "2026-10-17",
  ostatnieSprawdzenie: OSTATNIE_SPRAWDZENIE,
};
