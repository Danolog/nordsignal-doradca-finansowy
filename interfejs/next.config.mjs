/** @type {import('next').NextConfig} */

// GDZIE STOI SILNIK — ODPOWIEDZ ZALEZY OD MIEJSCA, W KTORYM DZIALAMY (W6).
//
// Do W6 stalo tu jedno przepisanie na `http://127.0.0.1:8000`, bez zadnego
// rozgalezienia. Na platformie prowadzilo DONIKAD — i bylo to zmierzone,
// nie przewidziane: wdrozenie produkcyjne 2026-08-29 odpowiadalo na
// `/api/zdrowie` kodem 404 z naglowkiem `x-vercel-error:
// DNS_HOSTNAME_RESOLVED_PRIVATE`. Platforma odmawia przepisania na adres
// petli zwrotnej, bo w chmurze `127.0.0.1` to sama funkcja, a nie nasz silnik.
//
// DLACZEGO PRZEPISANIE, A NIE ADRES BEZPOSREDNI W PRZEGLADARCE.
// `app/ksiegowanie/formularz.tsx` ma `"use client"` i zapisuje wpis Z
// PRZEGLADARKI (`zapiszWpis`, `wycofajWpis`, `pobierzPodglad`). Gdyby
// przegladarka wolala silnik pod jego wlasnym adresem, doszlaby polityka
// pochodzenia (CORS) do obejscia i druga powierzchnia do zabezpieczenia.
// Przepisanie daje przegladarce JEDEN adres — ten, na ktorym stoi aplikacja.
//
// JEDEN NOSNIK ADRESU SILNIKA: zmienna `ADRES_SILNIKA`. Ta sama zmienna, ktora
// czyta `lib/dane/warstwa-sieciowa.ts` dla wywolan po stronie serwera. Gdyby
// adres byl wpisany tutaj na sztywno, byloby to DRUGIE zrodlo odpowiedzi
// „gdzie stoi silnik", a rozjazd nie dalby zadnego sygnalu — czesc zadan
// szlaby gdzie indziej niz reszta.
//
// BRAK ZMIENNEJ NA PLATFORMIE PRZERYWA BUDOWANIE I TO JEST DECYZJA (§3.7).
// Przepisanie na `undefined/api/...` zbudowaloby sie bez slowa i dopiero
// uzytkownik zobaczylby ekran awarii. Wolimy czerwona budowe z instrukcja.
const NA_PLATFORMIE = process.env.VERCEL === "1";
const ADRES_SILNIKA = process.env.ADRES_SILNIKA;

if (NA_PLATFORMIE && !ADRES_SILNIKA) {
  throw new Error(
    "Nie wiem, gdzie stoi silnik: zmienna ADRES_SILNIKA jest pusta albo jej nie ma. " +
      "Ustaw ja w zmiennych srodowiskowych projektu na pelny adres wdrozenia " +
      "silnika (ze schematem https) i zbuduj ponownie. " +
      "Nie zgaduje adresu, bo silnik zgadniety wygladalby tak samo jak wlasciwy.",
  );
}

const CEL_PRZEPISANIA = NA_PLATFORMIE
  ? `${ADRES_SILNIKA}/api/:sciezka*`
  : "http://127.0.0.1:8000/api/:sciezka*";

const config = {
  // Znacznik trybu pracy lokalnej rysuje sie NA ekranie i wchodzi do zrzutu,
  // wiec bramka odwzorowania liczylaby go jako roznice wobec ramki. Zdejmujemy
  // go, zeby pomiar mierzyl ekran, a nie narzedzie.
  devIndicators: false,

  // Silnik jest w Pythonie i stoi obok jako funkcja. Przepisujemy wywolania
  // na niego, zeby przegladarka widziala jeden adres — lokalnie na port 8000,
  // na platformie na wdrozenie silnika.
  async rewrites() {
    return [{ source: "/api/:sciezka*", destination: CEL_PRZEPISANIA }];
  },
};
export default config;
