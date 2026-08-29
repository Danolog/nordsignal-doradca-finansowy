// EKRAN BUDZET — WEJSCIE. Uklad mieszka obok, w `ekran.tsx`.
//
// TEN PLIK PRZEJMUJE ADRES SAM, bez zadnej edycji gdzie indziej i bez
// zadnego wpisu do skasowania. `app/[ekran]/page.tsx` obsluguje ekrany,
// ktore mapa zna, a kodu jeszcze nie maja; segment STALY w Next wygrywa
// z segmentem z parametrem, wiec od chwili powstania tego pliku `/budzet`
// prowadzi tutaj, a nie na zdanie „Tej części jeszcze nie ma". Tak zostalo
// to zaprojektowane w W7 i tutaj jest sprawdzane po raz pierwszy.
//
// ROZDZIAL NA DWA PLIKI — wolanie decyzji z `app/ksiegowanie/page.tsx`, nie
// jej druga kopia: dane serwerowo (maja stac w pierwszym rysowaniu, inaczej
// pierwsze spojrzenie pada na pustke — §3.7), interakcja klienecko (kazdy
// z czterech zapisow oddaje CALY nowy ekran, wiec `DANE` musza byc stanem).
//
// `dzis` Z ADRESU ma nosnik po drugiej stronie: `api/wspolne.py::dzien` mowi
// wprost, ze parametr istnieje DLA POMIARU ODBIORCZEGO — bramka wymaga
// ustalonego dnia, zeby jej wynik nie zalezal od godziny przebiegu. Bez
// parametru silnik bierze dzien dzisiejszy.

import { Awaria } from "../awaria";
import { Ekran } from "./ekran";
import { pobierzBudzet } from "@/lib/dane/budzet";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import type { DaneBudzetu } from "@/lib/kontrakt";

export default async function Budzet({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const parametry = (await searchParams) ?? {};
  const dzis = typeof parametry.dzis === "string" ? parametry.dzis : null;

  let dane: DaneBudzetu;
  try {
    dane = await pobierzBudzet(dzis);
  } catch (blad) {
    // Awaria do stanu uzytecznego, nie do zera (CLAUDE.md §3.7). Ekran mowi,
    // czego brakuje i co zrobic; nie pokazuje pustej rubryki ani zera.
    if (blad instanceof BladWarstwySieciowej) {
      return <Awaria aktywny="budzet" czegoBrakuje={blad.czegoBrakuje} coZrobic={blad.coZrobic} />;
    }
    throw blad;
  }

  return <Ekran poczatkowe={dane} dzis={dzis} />;
}
