// KORZEN APLIKACJI — PRZEKIEROWANIE NA EKRAN STARTOWY, NIE DRUGI EKRAN.
//
// Do W7 stal tutaj CALY ekran Plynnosci, a pasek prowadzil na `/plynnosc`,
// gdzie nie bylo niczego. Zmierzone przed zmiana (2026-08-29, `curl` po
// wszystkich pozycjach): dziewiec z dziewieciu odsylaczy paska = HTTP 404,
// w tym odsylacz do ekranu, ktory wlasnie stal na wierzchu.
//
// DLACZEGO PRZEKIEROWANIE, A NIE DRUGA KOPIA EKRANU. Ekran ma jeden nosnik:
// `app/plynnosc/page.tsx`. Gdyby korzen renderowal go po raz drugi, ta sama
// tresc mialaby dwa adresy i dwa miejsca do poprawiania (CLAUDE.md §3.2).
//
// DLACZEGO NIE POLE `adres` W MAPIE EKRANOW. Pole musialoby niesc `/` dla
// plynnosci i `/${klucz}` dla pozostalych osmiu — czyli DRUGI NOSNIK faktu,
// ktory `klucz` juz niesie. `makiety/ekrany.py` odrzucil raz dokladnie taki
// pole (`aktywna_w_pasku`) i to samo uzasadnienie stosuje sie tutaj.
//
// PARAMETRY ADRESU PRZECHODZA DALEJ. `dzis` istnieje DLA POMIARU ODBIORCZEGO
// (`api/wspolne.py::dzien`), a bramka odwzorowania i straznik ekranu wolaja
// `/?dzis=…`. Przekierowanie gubiace parametr zmienialoby dzien pomiaru na
// dzisiejszy i bramka mierzylaby pogode, nie ekran.

import { redirect } from "next/navigation";
import { PASEK } from "@/lib/ekrany";

// Ekran startowy to PIERWSZA pozycja paska — ta sama, ktora mapa ekranow
// nazywa pytaniem zadawanym najczesciej. Wpisany tu klucz bylby drugim
// nosnikiem kolejnosci, ktora `PASEK` juz ustala.
const START = PASEK[0].klucz;

export default async function Korzen({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const parametry = (await searchParams) ?? {};
  const zapytanie = new URLSearchParams();
  for (const [nazwa, wartosc] of Object.entries(parametry)) {
    if (typeof wartosc === "string") zapytanie.set(nazwa, wartosc);
    else if (Array.isArray(wartosc)) for (const w of wartosc) zapytanie.append(nazwa, w);
  }
  const ogon = zapytanie.toString();
  redirect(ogon ? `/${START}?${ogon}` : `/${START}`);
}
