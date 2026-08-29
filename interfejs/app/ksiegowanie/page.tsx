// EKRAN KSIEGOWANIE — WEJSCIE. Uklad mieszka obok, w `formularz.tsx`.
//
// DLACZEGO ROZDZIAL NA DWA PLIKI. Formularz jest z natury kliencki: trzyma
// stan pol, reaguje na klikniecia i pyta o podglad w trakcie pisania. Dane
// wejsciowe sa z natury serwerowe: przychodza z `GET /api/ksiegowanie` i maja
// byc w pierwszym rysowaniu strony, a nie doczytane po nim. Jeden plik nie
// moze byc obiema rzeczami naraz, a gdyby formularz doczytywal dane sam,
// pierwsze rysowanie pokazywaloby ekran bez liczb — czyli pustke, ktorej
// CLAUDE.md §3.7 zabrania wprost.
//
// UKLAD NIE PRZESZEDL PRZEZ TE ZMIANE ANI JEDNYM WEZLEM. Plik `formularz.tsx`
// to `page.tsx` sprzed podpiecia, przeniesiony `git mv` — historia pokazuje
// zmiane jako zmiane nazwy, nie jako nowy plik.
//
// `dzis` Z ADRESU ma nosnik po drugiej stronie: `api/wspolne.py::dzien` mowi
// wprost, ze parametr istnieje DLA POMIARU ODBIORCZEGO. Bez niego silnik
// bierze dzien dzisiejszy.

import { Awaria } from "../awaria";
import { Formularz } from "./formularz";
import { pobierzKsiegowanie } from "@/lib/dane/ksiegowanie";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import type { DaneKsiegowania } from "@/lib/kontrakt";

export default async function Ksiegowanie({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const parametry = (await searchParams) ?? {};
  const dzis = typeof parametry.dzis === "string" ? parametry.dzis : null;

  let dane: DaneKsiegowania;
  try {
    dane = await pobierzKsiegowanie(dzis);
  } catch (blad) {
    if (blad instanceof BladWarstwySieciowej) {
      return (
        <Awaria aktywny="ksiegowanie" czegoBrakuje={blad.czegoBrakuje} coZrobic={blad.coZrobic} />
      );
    }
    throw blad;
  }

  return <Formularz poczatkowe={dane} dzis={dzis} />;
}
