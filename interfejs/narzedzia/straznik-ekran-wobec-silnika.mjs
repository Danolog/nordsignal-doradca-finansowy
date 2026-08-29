// STRAŻNIK: LICZBA NA EKRANIE = LICZBA Z SILNIKA.
//
// PO CO ISTNIEJE — luka nazwana wprost, nie domyślana. `testy/conftest.py`
// wypisuje w sekcji „czego nie przeniesiono z poprzednika": strażnik
// BEHAWIORALNY (`test_ekran_playwright.py`) nie przeszedł do tego projektu,
// a razem z nim zniknęło pilnowanie, ŻE LICZBA NA EKRANIE RÓWNA SIĘ WYNIKOWI
// SILNIKA. Bramka odwzorowania (`porownaj-z-makieta.mjs`) mierzy WYGLĄD:
// ekran pokazujący piękną, zgodną z ramką liczbę wziętą z powietrza
// przeszedłby ją na zielono. Strażnik źródłowy też jej nie łapie — zmierzone
// u poprzednika: podmiana argumentu `rezerwa` na `Decimal("0")` zawyżyła
// nagłówek o 5 768,11 zł i przeszła 532 testy.
//
// W CO TEN STRAŻNIK TRAFIA. W tekst WYRENDEROWANY w przeglądarce — w to samo,
// co widzi oko — porównany z odpowiedzią trasy odpytanej OSOBNO, w tej samej
// chwili i dla tego samego dnia. Nie porównuje z wartością wpisaną do testu:
// wartość wpisana starzeje się i po pierwszej zmianie danych mierzy przeszłość.
//
// ILE RZECZY WIDZI. Każdy przebieg wypisuje liczbę porównanych liczb i kończy
// się kodem 2 (błąd pomiaru), gdy jest ich mniej niż PROG_LICZNOSCI. Bez tego
// pusty ekran przechodziłby tak samo jak ekran poprawny — sprawdzenie, do
// którego nic nie dociera, melduje sukces.
//
// FORMATOWANIE WOŁA JEDEN NOŚNIK. `sformatujKwote`/`znakKwoty` importowane
// z `lib/kwota.ts` — tego samego pliku, którego używa ekran. Własna kopia
// reguły formatowania byłaby DRUGIM nośnikiem i przepuściłaby dokładnie te
// wady, których ma pilnować (na przykład zgubiony grosz).
//
// Uruchomienie:
//   node narzedzia/straznik-ekran-wobec-silnika.mjs [dzis]
//   node narzedzia/straznik-ekran-wobec-silnika.mjs 2026-09-02
//
// Kody wyjścia: 0 — zgodne · 1 — rozjazd liczby · 2 — błąd pomiaru.

import { chromium } from "playwright";
import { sformatujKwote, znakKwoty } from "../lib/kwota.ts";

const EKRAN = process.env.ADRES_EKRANU ?? "http://localhost:3000";
const SILNIK = process.env.ADRES_SILNIKA ?? "http://127.0.0.1:8000";

//: Poniżej tego progu przebieg jest błędem pomiaru, nie sukcesem.
//: Księga w stanie z kotwicą ma co najmniej wiersz otwarcia z saldem
//: i jedną pozycję z kwotą i saldem — czyli minimum trzy liczby.
const PROG_LICZNOSCI = 3;

function znak(kwota) {
  return sformatujKwote(kwota, znakKwoty(kwota));
}

/** Liczby, których OCZEKUJEMY na ekranie — złożone z odpowiedzi trasy. */
function oczekiwane(dane) {
  const wiersze = dane.ksiega.map((p) => ({
    kwota: p.kwota === null ? "—" : znak(p.kwota),
    saldo: p.saldoPoDniu === null ? "" : sformatujKwote(p.saldoPoDniu, "neutralna"),
  }));
  const zamkniecie =
    dane.saldoMinimalne === null ? null : znak(dane.saldoMinimalne);
  return { wiersze, zamkniecie };
}

/** Liczby, które NAPRAWDĘ stoją na wyrenderowanym ekranie. */
async function zEkranu(strona) {
  return strona.evaluate(() => {
    const tekst = (e) => (e ? e.textContent.replace(/ /g, " ").trim() : null);
    const ksiega = document.querySelector('[class*="__ksiega"]');
    if (!ksiega) return { blad: "nie ma bloku księgi na ekranie" };

    const wiersze = [...ksiega.children]
      .filter((e) => /__wiersz(?![A-Z])/.test(e.className))
      .map((w) => {
        const komorki = [...w.children];
        return {
          kwota: tekst(komorki.find((k) => /__komorkaKwoty|__komorkaBezKwoty/.test(k.className))),
          saldo: tekst(komorki.find((k) => /__komorkaSalda/.test(k.className))),
        };
      });

    const z = ksiega.querySelector('[class*="__liczbaZamkniecia"]');
    return { wiersze, zamkniecie: tekst(z) };
  });
}

function porownaj(oczek, zekranu) {
  const rozjazdy = [];
  let porownanych = 0;

  if (oczek.wiersze.length !== zekranu.wiersze.length) {
    rozjazdy.push(
      `LICZNOSC_WIERSZY: silnik oddał ${oczek.wiersze.length} pozycji księgi, ` +
        `ekran narysował ${zekranu.wiersze.length}`,
    );
  }

  const ile = Math.min(oczek.wiersze.length, zekranu.wiersze.length);
  for (let i = 0; i < ile; i += 1) {
    for (const pole of ["kwota", "saldo"]) {
      const a = oczek.wiersze[i][pole];
      const b = zekranu.wiersze[i][pole] ?? "";
      if (a === "" && b === "") continue;      // saldo bite raz na dzień
      porownanych += 1;
      if (a !== b) rozjazdy.push(`KSIEGA[${i}].${pole}: silnik „${a}", ekran „${b}"`);
    }
  }

  if (oczek.zamkniecie !== null) {
    porownanych += 1;
    if (oczek.zamkniecie !== zekranu.zamkniecie) {
      rozjazdy.push(
        `WIERSZ_ZAMKNIECIA: silnik „${oczek.zamkniecie}", ekran „${zekranu.zamkniecie}"`,
      );
    }
  }
  return { rozjazdy, porownanych };
}

async function glowna() {
  const dzis = process.argv[2] ?? null;
  const parametr = dzis ? `?dzis=${encodeURIComponent(dzis)}` : "";

  let dane;
  try {
    const odp = await fetch(`${SILNIK}/api/plynnosc${parametr}`, { cache: "no-store" });
    if (!odp.ok) throw new Error(`trasa odpowiedziała kodem ${odp.status}`);
    dane = await odp.json();
  } catch (blad) {
    console.error(`BŁĄD POMIARU: nie mam odpowiedzi silnika — ${blad.message}`);
    process.exit(2);
  }

  const przegladarka = await chromium.launch();
  let kod = 0;
  try {
    const strona = await przegladarka.newPage({ viewport: { width: 1440, height: 900 } });
    const odp = await strona.goto(`${EKRAN}/${parametr}`, { waitUntil: "networkidle" });
    if (!odp || !odp.ok()) {
      console.error(`BŁĄD POMIARU: ekran odpowiedział kodem ${odp ? odp.status() : "—"}`);
      process.exit(2);
    }

    const zek = await zEkranu(strona);
    if (zek.blad) {
      console.error(`BŁĄD POMIARU: ${zek.blad}`);
      process.exit(2);
    }

    const oczek = oczekiwane(dane);
    const { rozjazdy, porownanych } = porownaj(oczek, zek);

    console.log(`Dzień odniesienia: ${dzis ?? "dzisiejszy (bez parametru)"}`);
    console.log(`Pozycji księgi z silnika: ${oczek.wiersze.length}`);
    console.log(`Pozycji księgi na ekranie: ${zek.wiersze.length}`);
    console.log(`Porównanych liczb: ${porownanych}`);
    console.log(`Wiersz zamknięcia: silnik „${oczek.zamkniecie}" · ekran „${zek.zamkniecie}"`);

    if (porownanych < PROG_LICZNOSCI) {
      console.error(
        `BŁĄD POMIARU: porównano ${porownanych} liczb, próg to ${PROG_LICZNOSCI} — ` +
          "to nie jest zgodność, to ślepy pomiar. Ekran bez kotwicy nie ma czego pokazać; " +
          "zapisz odczyt salda (PUT /api/kotwica) przed przebiegiem.",
      );
      process.exit(2);
    }

    if (rozjazdy.length) {
      console.log("WYNIK: ROZJAZD — ekran pokazuje inną liczbę niż policzył silnik:");
      for (const r of rozjazdy) console.log(`  ${r}`);
      kod = 1;
    } else {
      console.log("WYNIK: zgodne — każda liczba na ekranie równa się liczbie z silnika.");
    }
  } catch (blad) {
    console.error(`BŁĄD POMIARU: ${blad.message}`);
    kod = 2;
  } finally {
    await przegladarka.close();
  }
  process.exit(kod);
}

glowna();
