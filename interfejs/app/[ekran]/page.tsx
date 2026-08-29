// EKRAN, KTORY MAPA ZNA, A KODU JESZCZE NIE MA (W7).
//
// PO CO TA TRASA ISTNIEJE. Pasek renderuje `href={`/${klucz}`}` dla kazdej
// pozycji mapy ekranow. Zbudowane sa dwa ekrany z jedenastu, wiec przed W7
// dziewiec z dziewieciu odsylaczy paska konczylo sie surowa strona Next po
// angielsku (pomiar `curl`, 2026-08-29). Pasek obiecywal miejsce i nie
// dotrzymywal — a §3.7 zabrania konczyc na pustce.
//
// DLACZEGO TRASA Z PARAMETREM, A NIE DZIEWIEC ATRAP. Dziewiec plikow
// `app/<klucz>/page.tsx` z tym samym zdaniem byloby dziewiecioma kopiami
// jednej reguly (§3.2) — i kazdy z nich trzeba by pamietac o skasowaniu
// w dniu, w ktorym ekran naprawde powstanie. Ta trasa znika sama: segment
// stały w Next wygrywa z segmentem z parametrem, wiec `app/budzet/page.tsx`
// przejmie `/budzet` w chwili, w ktorej ktos go napisze, bez zadnej edycji
// tutaj i bez zadnego wpisu do skasowania.
//
// ZERO WPISANEJ LISTY EKRANOW. Nazwy, pytania i kolejnosc przychodza
// z `lib/ekrany.ts` — jedynego nosnika mapy po stronie interfejsu. Lista
// wpisana tutaj rozjechalaby sie z paskiem po pierwszej zmianie nazwy
// i nie zlapalby tego zaden straznik (`test_mapa_ekranow_NIE_ROZJECHALA_
// sie_miedzy_jezykami` porownuje `ekrany.py` z `ekrany.ts`, nie z ekranami).
// Pilnuje tego `testy/test_odsylacze_paska.py`.
//
// STAN „TU JESTEM" DOSTAJE POZYCJA, NA KTORA UZYTKOWNIK KLIKNAL. Adres jest
// jego adresem, wiec pasek mowi prawde: jestes w Miesiacu, tylko Miesiaca
// jeszcze nie ma. `co-mnie-czeka` nie jest pozycja paska, wiec nie zapala
// niczego — a gdy powstanie jako ekran, zapali PLYNNOSC z wlasnego pliku,
// tak jak rysuje to ramka `CoMnieCzeka.dc.html`.

import { notFound } from "next/navigation";
import { BezEkranu } from "../bez-ekranu";
import { AKCJA, CO_MNIE_CZEKA, PASEK, type Ekran } from "@/lib/ekrany";
import { NAPISY_NIEZBUDOWANEGO } from "@/lib/napisy";

/** Wszystko, co mapa ekranow zna po nazwie: pasek, akcja i rozwiniecia. */
const ZNANE: readonly Ekran[] = [...PASEK, AKCJA, CO_MNIE_CZEKA];

export default async function BrakEkranu({
  params,
}: {
  params: Promise<{ ekran: string }>;
}) {
  const { ekran } = await params;
  const znany = ZNANE.find((e) => e.klucz === ekran);

  // Adres spoza mapy nie jest „jeszcze niezbudowany" — jest nieznany, i to
  // jest inna wiadomosc. Rozstrzyga `app/not-found.tsx`.
  if (!znany) notFound();

  return (
    <BezEkranu
      aktywny={znany.klucz}
      tytul={NAPISY_NIEZBUDOWANEGO.tytul}
      zdanie={NAPISY_NIEZBUDOWANEGO.zdanie(znany.napis, znany.pytanie)}
      instrukcja={NAPISY_NIEZBUDOWANEGO.instrukcja(PASEK[0].napis)}
    />
  );
}
