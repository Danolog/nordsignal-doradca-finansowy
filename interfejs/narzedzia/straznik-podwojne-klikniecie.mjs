// STRAŻNIK D-64: DWA KLIKNIĘCIA „ZAPISZ WPIS" NIE MOGĄ DAĆ DWÓCH WPISÓW.
//
// PO CO ISTNIEJE. `POST /api/wpisy` nie jest idempotentne — dwa żądania dają
// dwa wpisy (zgłoszenie Maxa z Z6, potwierdzone pomiarem niżej). Klucz
// idempotentności po stronie silnika jest poza v1 (D-64), więc do v1 jedyną
// obroną jest blokada po stronie ekranu. Powód nie jest kosmetyczny:
// podwójny wpis fałszuje wykonanie planu, a po podziale osi (D-60/D-61)
// także samą prognozę — w aplikacji, której jedynym zadaniem jest powiedzieć,
// ile naprawdę zostało.
//
// W CO TEN STRAŻNIK TRAFIA. W LICZBĘ WPISÓW W BAZIE, odczytaną przez trasę
// przed i po — nie w atrybut `disabled` przycisku i nie w liczbę wierszy
// narysowanych na ekranie. Atrybut mówi o wyglądzie, a wpis fałszywy powstaje
// w bazie. Zmierzone 2026-08-29 na wersji sprzed naprawy: przycisk miał po
// trzech kliknięciach `disabled === false` i przeszły wszystkie trzy —
// strażnik pytający o atrybut zameldowałby wtedy dokładnie to samo co teraz.
//
// DLACZEGO TRZY `.click()` W JEDNYM ZADANIU, A NIE DWA KLIKNIĘCIA MYSZĄ.
// Playwright między dwoma `click()` oddaje sterowanie pętli zdarzeń, więc
// React zdąży przerysować przycisk i pomiar zmierzyłby `disabled`, a nie
// zamek. Trzy wywołania w jednym `evaluate` biegną w JEDNYM zadaniu
// przeglądarki — to jest najostrzejszy przypadek, jaki ten ekran może
// zobaczyć, i tylko on odróżnia zamek na `useRef` od zamka na stanie.
//
// KONTROLA LICZNOŚCI. Przebieg kończy się kodem 2 (błąd pomiaru), gdy nie
// powstał ANI JEDEN wpis: „zero przyrostu" wygląda identycznie dla ekranu,
// który poprawnie zablokował dublet, i dla ekranu, który nie zapisał nic,
// bo formularz się nie wypełnił albo silnik nie odpowiedział. Sprawdzenie,
// do którego nic nie dociera, melduje sukces.
//
// SPRZĄTA PO SOBIE: wpis powstały w tym przebiegu jest wycofywany trasą
// `DELETE /api/wpisy/{id}`, a przebieg wypisuje stan bazy po sprzątaniu.
//
// Uruchomienie (silnik i interfejs muszą stać):
//   node narzedzia/straznik-podwojne-klikniecie.mjs 2026-10-06
//
// Kody wyjścia: 0 — jeden wpis · 1 — dublet · 2 — błąd pomiaru.

import { chromium } from "playwright";

const EKRAN = process.env.ADRES_EKRANU ?? "http://localhost:3000";
const SILNIK = process.env.ADRES_SILNIKA ?? "http://127.0.0.1:8000";
const DZIS = process.argv[2] ?? null;
const PARAMETR = DZIS ? `?dzis=${encodeURIComponent(DZIS)}` : "";

//: Kwota z cyframi, które nie powtarzają się w innych kwotach tego ekranu —
//: żeby wpis tego przebiegu dało się rozpoznać wśród cudzych.
const KWOTA = "313,13";
const KATEGORIA = process.argv[3] ?? "Zakupy";
const ILE_KLIKNIEC = 3;

async function stanBazy() {
  const odp = await fetch(`${SILNIK}/api/ksiegowanie${PARAMETR}`, { cache: "no-store" });
  if (!odp.ok) throw new Error(`trasa /api/ksiegowanie odpowiedziała kodem ${odp.status}`);
  const dane = await odp.json();
  return {
    licznik: dane.liczbaWpisowWMiesiacu,
    nasze: dane.ostatnieWpisy.filter((w) => w.kwota === "313.13"),
  };
}

let kod = 0;
let przegladarka = null;
try {
  const przed = await stanBazy();
  przegladarka = await chromium.launch();
  const strona = await przegladarka.newPage({ viewport: { width: 1440, height: 900 } });

  const zadania = [];
  strona.on("request", (r) => {
    const u = r.url();
    if (r.method() === "POST" && u.includes("/api/wpisy") && !u.includes("podglad")) zadania.push(u);
  });

  const odp = await strona.goto(`${EKRAN}/ksiegowanie${PARAMETR}`, { waitUntil: "networkidle" });
  if (!odp || !odp.ok()) throw new Error(`ekran odpowiedział kodem ${odp ? odp.status() : "—"}`);

  await strona.fill('input[inputmode="decimal"]', KWOTA);
  await strona.click(`button[role="radio"]:has-text("${KATEGORIA}")`);
  await strona.waitForTimeout(800);   // podgląd z trasy

  const poKliknieciach = await strona.evaluate((ile) => {
    const p = [...document.querySelectorAll("button")].find((b) =>
      b.textContent.includes("Zapisz wpis"));
    if (!p) return { blad: "nie ma przycisku Zapisz wpis na ekranie" };
    for (let i = 0; i < ile; i += 1) p.click();
    return { wylaczony: p.disabled };
  }, ILE_KLIKNIEC);
  if (poKliknieciach.blad) throw new Error(poKliknieciach.blad);

  await strona.waitForTimeout(2500);
  const po = await stanBazy();
  const przyrost = po.licznik - przed.licznik;

  console.log(`Dzień odniesienia: ${DZIS ?? "dzisiejszy (bez parametru)"}`);
  console.log(`Kliknięć w jednym zadaniu przeglądarki: ${ILE_KLIKNIEC}`);
  console.log(`Żądań POST /api/wpisy wysłanych z przeglądarki: ${zadania.length}`);
  console.log(`Przycisk „Zapisz wpis" wyłączony bezpośrednio po kliknięciach: ${poKliknieciach.wylaczony}`);
  console.log(`Wpisów w miesiącu: przed ${przed.licznik} · po ${po.licznik} · przyrost ${przyrost}`);

  // Sprzątanie PRZED werdyktem — żeby czerwony przebieg też nie zostawiał śmieci.
  for (const w of po.nasze) {
    await fetch(`${SILNIK}/api/wpisy/${w.id}${PARAMETR}`, { method: "DELETE" });
  }
  const poSprzataniu = await stanBazy();
  console.log(`Po sprzątnięciu wpisów tego przebiegu: ${poSprzataniu.licznik}`);

  if (przyrost === 0) {
    console.error(
      "BŁĄD POMIARU: nie powstał ANI JEDEN wpis. To nie jest dowód, że dublet " +
        "został zablokowany — tak samo wygląda formularz, który się nie wypełnił, " +
        "i silnik, który nie zapisał. Sprawdzenie, do którego nic nie dociera, " +
        "melduje sukces.",
    );
    kod = 2;
  } else if (przyrost > 1) {
    console.log(
      `WYNIK: DUBLET — ${ILE_KLIKNIEC} kliknięcia dały ${przyrost} wpisy. ` +
        "Podwójny wpis fałszuje wykonanie planu i prognozę (D-64).",
    );
    kod = 1;
  } else {
    console.log("WYNIK: jeden wpis — zamek trzyma.");
  }
} catch (blad) {
  console.error(`BŁĄD POMIARU: ${blad.message}`);
  kod = 2;
} finally {
  if (przegladarka) await przegladarka.close();
}
process.exit(kod);
