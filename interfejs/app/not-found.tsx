// ADRES SPOZA MAPY EKRANOW (W7, §3.7).
//
// Trafia tu wszystko, czego `lib/ekrany.ts` nie zna po nazwie: literowka
// w adresie, stara zakladka, odsylacz spoza aplikacji. Adres ZNANY z mapy,
// ale jeszcze niezbudowany, konczy gdzie indziej — w `app/[ekran]/page.tsx` —
// bo „nie ma czegos takiego" i „jeszcze tego nie zrobilem" to dwie rozne
// wiadomosci i prowadza do dwoch roznych ruchow uzytkownika.
//
// Do W7 stala tu strona wbudowana w Next: „404: This page could not be
// found." Po angielsku, bez zdania o tym, co zrobic — czyli pustka, ktorej
// §3.7 zabrania, w aplikacji pisanej po polsku dla jednej osoby.
//
// PASEK ZOSTAJE, ZADNA POZYCJA SIE NIE ZAPALA. Uzytkownik jest pod adresem,
// ktory do zadnego obszaru nie nalezy — zapalona pozycja klamalaby o tym,
// gdzie stoi. To jedyne miejsce w aplikacji, w ktorym stan „tu jestem" ma
// prawo nie wskazywac niczego.

import { BezEkranu } from "./bez-ekranu";
import { PASEK } from "@/lib/ekrany";
import { NAPISY_NIEZNANEGO_ADRESU } from "@/lib/napisy";

export default function NieznanyAdres() {
  return (
    <BezEkranu
      aktywny=""
      tytul={NAPISY_NIEZNANEGO_ADRESU.tytul}
      zdanie={NAPISY_NIEZNANEGO_ADRESU.zdanie}
      instrukcja={NAPISY_NIEZNANEGO_ADRESU.instrukcja(PASEK[0].napis)}
    />
  );
}
