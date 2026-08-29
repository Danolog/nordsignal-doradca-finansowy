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
// CO DOSZŁO W Z7c: STOPKA OBU EKRANÓW. „Ostatnie sprawdzenie" nie jest kwotą,
// ale jest odpowiedzią na to samo pytanie co liczby wyżej — „czy to, co widzę,
// jest aktualne" — i do Z7c dwa ekrany dawały na nie dwie różne odpowiedzi:
// Płynność czytała pole z silnika, a Księgowanie podawało na sztywno `null`
// i mówiło „nie wiem" o czymś, co aplikacja wiedziała. Sprawdzenie stoi TUTAJ,
// a nie w bramce odwzorowania, bo bramka mierzy piksele: ZMIERZONE 2026-08-29
// na mutacji M-Z7c-6 (stopka odpięta) — sama bramka pikselowa dała 0,29%
// przy progu 2%, czyli PRZESZŁA. Wygląd nie jest nośnikiem tej reguły.
//
// CO DOSZŁO W W8: STRAŻNIK SAM STAWIA STAN, KTÓRY MIERZY.
// Do W8 przebieg na czystej bazie kończył się kodem 2 („zapisz odczyt salda
// PRZED przebiegiem") — bo bez kotwicy prognozy nie ma, księga jest pusta
// i porównywać nie ma czego. Znaczyło to, że najczęstszy stan aplikacji —
// świeża baza — był stanem, w którym strażnik NIE PATRZY. Wymóg ręcznego
// kroku przed pomiarem jest tym samym co brak pomiaru: pierwszy przebieg,
// przy którym ktoś tego kroku nie zrobi, zamelduje błąd, a nie wadę.
// Od W8 ekran ma kontrolkę stanu konta, więc strażnik doprowadza się do
// stanu mierzalnego SAM — tą samą drogą, którą przechodzi człowiek:
// klika „Podaj stan konta", wpisuje odczyt, zapisuje. Ten krok jest
// wypisywany w logu, bo zmienia dane w bazie.
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

//: Odczyt, którym strażnik doprowadza pustą bazę do stanu mierzalnego (W8).
//: Wartość jest własnością POMIARU, nie aplikacji — dlatego stoi tutaj,
//: a nie w `lib/dane/`, gdzie po Z7 nie ma ani jednej kwoty.
const ODCZYT_STARTOWY = "9920,79";
//: Brzmienie wezwania z `lib/napisy.ts` (`NAPISY_KOTWICY.podaj`) i z ramki
//: `makiety/NieWiem.dc.html`. Powtórzone tutaj świadomie: strażnik ma trafiać
//: w to, co WIDZI CZŁOWIEK, a import z modułu ekranu uczyniłby go ślepym na
//: rozjazd między napisem a ramką. Rozjazdu pilnuje osobno
//: `testy/test_ekran_plynnosc.py::test_wezwanie_MA_BRZMIENIE_Z_RAMKI`.
const WEZWANIE_KOTWICY = "Podaj stan konta";

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

/** Zdanie stopki wyrenderowane na ekranie — albo `null`, gdy stopki nie ma. */
async function stopkaZEkranu(strona) {
  return strona.evaluate(() => {
    const e = document.querySelector(".straznik");
    return e ? e.textContent.replace(/\u00a0/g, " ").trim() : null;
  });
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

  let dane;   // `let`, bo po postawieniu kotwicy odpytujemy silnik ponownie
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

    // STAN MIERZALNY STAWIAMY SAMI (W8). Bez kotwicy księga jest pusta,
    // więc porównanie nie miałoby czego porównać. Wchodzimy tą samą drogą
    // co człowiek — przez kontrolkę na ekranie, nie przez trasę: dzięki temu
    // przebieg dowodzi przy okazji, że kontrolka DZIAŁA. Wpis do bazy jest
    // wypisany, bo to zmiana danych, a nie odczyt.
    if (dane.saldoMinimalne === null) {
      const wezwanie = strona.locator(`button:has-text("${WEZWANIE_KOTWICY}")`);
      if ((await wezwanie.count()) === 0) {
        console.error(
          `BŁĄD POMIARU: prognoza nie ma punktu startu, a na ekranie nie ma wezwania ` +
            `„${WEZWANIE_KOTWICY}". Do W8 trzeba było zapisać odczyt ręcznie; ` +
            "jeśli kontrolka zniknęła, to jest wada, nie brak danych.",
        );
        process.exit(2);
      }
      console.log(
        `STAN POSTAWIONY PRZEZ STRAŻNIKA: brak kotwicy → wpisuję ${ODCZYT_STARTOWY} zł ` +
          "przez kontrolkę na ekranie (to zmienia dane w bazie).",
      );
      await wezwanie.click();
      await strona.locator('input[inputmode="decimal"]').fill(ODCZYT_STARTOWY);
      await strona.keyboard.press("Enter");
      await strona.waitForTimeout(1200);

      // Silnik odpytujemy PONOWNIE, bo mierzymy ekran wobec liczby, którą
      // silnik ma TERAZ — nie wobec tej sprzed zapisu.
      const odpNowa = await fetch(`${SILNIK}/api/plynnosc${parametr}`, { cache: "no-store" });
      if (!odpNowa.ok) {
        console.error(`BŁĄD POMIARU: po zapisie kotwicy trasa odpowiedziała ${odpNowa.status}`);
        process.exit(2);
      }
      dane = await odpNowa.json();
      if (dane.saldoMinimalne === null) {
        console.error(
          "BŁĄD POMIARU: kontrolka stanu konta nie zapisała odczytu — " +
            "prognoza nadal nie ma punktu startu. To jest wada kontrolki.",
        );
        process.exit(2);
      }
    }

    const zek = await zEkranu(strona);
    if (zek.blad) {
      console.error(`BŁĄD POMIARU: ${zek.blad}`);
      process.exit(2);
    }

    const oczek = oczekiwane(dane);
    const { rozjazdy, porownanych } = porownaj(oczek, zek);

    // --- stopka na OBU ekranach ---
    const stopkaPlynnosci = await stopkaZEkranu(strona);
    let daneKsiegowania;
    try {
      const o = await fetch(`${SILNIK}/api/ksiegowanie${parametr}`, { cache: "no-store" });
      if (!o.ok) throw new Error(`trasa odpowiedziała kodem ${o.status}`);
      daneKsiegowania = await o.json();
    } catch (blad) {
      console.error(`BŁĄD POMIARU: nie mam odpowiedzi /api/ksiegowanie — ${blad.message}`);
      process.exit(2);
    }
    const odp2 = await strona.goto(`${EKRAN}/ksiegowanie${parametr}`, { waitUntil: "networkidle" });
    if (!odp2 || !odp2.ok()) {
      console.error(`BŁĄD POMIARU: ekran Księgowania odpowiedział kodem ${odp2 ? odp2.status() : "—"}`);
      process.exit(2);
    }
    const stopkaKsiegowania = await stopkaZEkranu(strona);
    if (stopkaPlynnosci === null || stopkaKsiegowania === null) {
      console.error("BŁĄD POMIARU: nie widzę stopki na jednym z ekranów — pomiar nic nie porównał.");
      process.exit(2);
    }
    // ILE STOPEK POMIAR NAPRAWDĘ POROWNAŁ. Gdy silnik nie ma ani jednego
    // przebiegu strażnika, oba ekrany pokazują ten sam stały napis „nie wiem" —
    // i porównanie ich ze sobą przechodzi także wtedy, gdy jeden z nich ma
    // to zdanie WPISANE NA SZTYWNO. Taki przebieg NIE JEST dowodem i mówi
    // o tym wprost, zamiast doliczać się do sukcesu.
    let stopekPorownanych = 0;
    for (const [nazwa, naEkranie, zSilnika] of [
      ["PLYNNOSC", stopkaPlynnosci, dane.ostatnieSprawdzenie],
      ["KSIEGOWANIE", stopkaKsiegowania, daneKsiegowania.ostatnieSprawdzenie],
    ]) {
      if (zSilnika === null) continue;      // patrz wyżej — ślepy przypadek
      stopekPorownanych += 1;
      if (naEkranie !== zSilnika) {
        rozjazdy.push(`STOPKA[${nazwa}]: silnik „${zSilnika}", ekran „${naEkranie}"`);
      }
    }
    // Pytanie osobne, bo oba ekrany mogą zgadzać się ze swoim silnikiem
    // i mimo to mówić co innego — dokładnie tak było do Z7b, gdy kontrakt
    // Księgowania nie miał tego pola w ogóle.
    if (stopkaPlynnosci !== stopkaKsiegowania) {
      rozjazdy.push(
        `STOPKA[DWA EKRANY]: Płynność „${stopkaPlynnosci}", Księgowanie „${stopkaKsiegowania}" — ` +
          "dwie odpowiedzi na jedno pytanie o aktualność tego, co widać",
      );
    }

    console.log(`Dzień odniesienia: ${dzis ?? "dzisiejszy (bez parametru)"}`);
    console.log(`Pozycji księgi z silnika: ${oczek.wiersze.length}`);
    console.log(`Pozycji księgi na ekranie: ${zek.wiersze.length}`);
    console.log(`Porównanych liczb: ${porownanych}`);
    console.log(`Wiersz zamknięcia: silnik „${oczek.zamkniecie}" · ekran „${zek.zamkniecie}"`);
    console.log(
      `Porównanych stopek: ${stopekPorownanych}` +
        (stopekPorownanych === 2
          ? ""
          : "  — ŚLEPY PRZYPADEK: silnik nie ma przebiegu strażnika, więc oba ekrany " +
            "pokazują ten sam stały napis o niewiedzy. Zgodność stopek NIE jest tu dowodem; " +
            "żeby nim była, w bazie musi stać wiersz w `przebiegi_straznika`."),
    );
    console.log(`  Płynność:    „${stopkaPlynnosci}"`);
    console.log(`  Księgowanie: „${stopkaKsiegowania}"`);

    if (porownanych < PROG_LICZNOSCI) {
      console.error(
        `BŁĄD POMIARU: porównano ${porownanych} liczb, próg to ${PROG_LICZNOSCI} — ` +
          "to nie jest zgodność, to ślepy pomiar. Od W8 strażnik sam stawia kotwicę " +
          "przez kontrolkę na ekranie, więc pusta księga PO tym kroku znaczy, że zapis " +
          "nie zadziałał albo ekran nie dostał odświeżonych danych — to jest wada, " +
          "nie brak danych.",
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
