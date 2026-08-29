// EKRAN PLYNNOSC — WEJSCIE. Uklad mieszka obok, w `ekran.tsx`.
//
// DLACZEGO ROZDZIAL NA DWA PLIKI (W8). Dane wejsciowe sa z natury serwerowe:
// przychodza z `GET /api/plynnosc` i maja stac w PIERWSZYM rysowaniu strony,
// a nie doczytywac sie po nim — inaczej pierwsze spojrzenie pada na pustke,
// ktorej CLAUDE.md §3.7 zabrania wprost. Uklad jest od W8 z natury kliencki:
// kontrolka stanu konta trzyma stan pol, a odpowiedz `PUT /api/kotwica`
// przynosi CALY nowy ekran. Jeden plik nie moze byc obiema rzeczami naraz.
//
// Wzorzec ten sam co w `app/ksiegowanie/page.tsx` — i to jest wolanie tamtej
// decyzji, nie druga jej kopia: rozstrzygniecie „dane serwerowo, interakcja
// klienecko" ma jeden nosnik i jest nim tamten naglowek.
//
// GDZIE TEN EKRAN STOI (W7). Do W7 lezal pod `app/page.tsx`, czyli pod `/`,
// a pasek prowadzil na `/plynnosc`, gdzie nie bylo niczego. Ekran przeniesiony
// pod swoj wlasny klucz; `app/page.tsx` zostalo przekierowaniem.
//
// `dzis` Z ADRESU ma nosnik po drugiej stronie: `api/wspolne.py::dzien` mowi
// wprost, ze parametr istnieje DLA POMIARU ODBIORCZEGO. Bez niego silnik
// bierze dzien dzisiejszy.

import { Awaria } from "../awaria";
import { Ekran } from "./ekran";
import { pobierzPlynnosc } from "@/lib/dane/plynnosc";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import type { DanePlynnosci } from "@/lib/kontrakt";

export default async function Plynnosc({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const parametry = (await searchParams) ?? {};
  const dzis = typeof parametry.dzis === "string" ? parametry.dzis : null;

  let dane: DanePlynnosci;
  try {
    dane = await pobierzPlynnosc(dzis);
  } catch (blad) {
    // Awaria do stanu uzytecznego, nie do zera (CLAUDE.md §3.7). Ekran mowi,
    // czego brakuje i co zrobic; nie pokazuje pustej rubryki ani zera.
    if (blad instanceof BladWarstwySieciowej) {
      return <Awaria aktywny="plynnosc" czegoBrakuje={blad.czegoBrakuje} coZrobic={blad.coZrobic} />;
    }
    throw blad;
  }

  return <Ekran poczatkowe={dane} dzis={dzis} />;
}
