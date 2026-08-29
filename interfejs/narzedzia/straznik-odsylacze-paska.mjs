// STRAŻNIK ODSYŁACZY PASKA — czy każdy prowadzi tam, gdzie obiecuje (W7).
//
// DLACZEGO PRZEJŚCIEM, A NIE CZYTANIEM KODU. Zdanie „pasek renderuje
// `href={`/${klucz}`}`, a trasy istnieją, więc działa" jest prawdziwe
// i bezużyteczne: nie mówi, co użytkownik zobaczy. Przed W7 ten sam kod
// dawał dziewięć razy angielską stronę „404: This page could not be found."
// Ten strażnik KLIKA — bierze adresy z wyrenderowanego nagłówka i wchodzi
// pod każdy z nich.
//
// KONTROLA LICZNOŚCI JEST TU WARUNKIEM, NIE OZDOBĄ. Sprawdzenie, do którego
// nic nie dociera, melduje sukces: pusty pasek przeszedłby „zero błędnych
// odsyłaczy" tak samo jak pasek kompletny. Dlatego przebieg, w którym pasek
// oddał inną liczbę odsyłaczy niż mapa ekranów (`lib/ekrany.ts`), kończy się
// kodem 2 — BŁĄD POMIARU, nie sukces i nie porażka.
//
// CO UZNAJEMY ZA „PROWADZI TAM, GDZIE OBIECUJE":
//   (a) odpowiedź nie jest błędem sieci ani stroną wbudowaną w Next;
//   (b) na ekranie stoi POWŁOKA — znak słowny i pasek — czyli użytkownik
//       ma czym wyjść dalej jednym klikiem (§3.7);
//   (c) na ekranie NIE MA angielskiego zdania Next „This page could not be
//       found" ani gołego „404";
//   (d) ekran mówi po polsku, co się stało: albo jest treścią, albo niesie
//       zdanie o tym, że tej części jeszcze nie ma.
//
// ADRES SPOZA MAPY jest sprawdzany osobno i ma OBOWIĄZEK oddać kod 404 —
// razem z polskim zdaniem. Kod 200 na nieznanym adresie byłby kłamstwem
// wobec przeglądarki i wyszukiwarki, a polskie zdanie bez kodu 404 uczyłoby,
// że każdy adres jest poprawny.
//
// Uruchomienie:
//   node narzedzia/straznik-odsylacze-paska.mjs
//   ADRES_EKRANU=https://… node narzedzia/straznik-odsylacze-paska.mjs
// Kody wyjścia: 0 — wszystkie prowadzą · 1 — któryś nie prowadzi · 2 — błąd pomiaru.

import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

const EKRAN = process.env.ADRES_EKRANU ?? "http://localhost:3000";
const KATALOG = path.dirname(fileURLToPath(import.meta.url));
const MAPA = path.join(KATALOG, "..", "lib", "ekrany.ts");

/** Adres, którego mapa ekranów na pewno nie zna — do kontroli drugiej strony. */
const ADRES_SPOZA_MAPY = "/nie-ma-takiego-ekranu-i-nigdy-nie-bylo";

const ZDANIA_NEXT = ["This page could not be found", "Not Found"];

/** Ile pozycji ma mieć pasek — czytane z mapy, nie wpisane tutaj. */
async function licznoscZMapy() {
  const tekst = await fs.readFile(MAPA, "utf-8");
  const poczatek = tekst.indexOf("export const PASEK");
  if (poczatek < 0) throw new Error(`nie znalazłem PASEK w ${MAPA}`);
  const koniec = tekst.indexOf("] as const;", poczatek);
  const blok = tekst.slice(poczatek, koniec);
  return [...blok.matchAll(/klucz:\s*"([^"]+)"/g)].map((m) => m[1]);
}

async function wejdz(strona, adres) {
  const odp = await strona.goto(`${EKRAN}${adres}`, { waitUntil: "networkidle" });
  const kod = odp ? odp.status() : null;
  const tekst = await strona.evaluate(() => document.body.innerText);
  const maPowloke = await strona.evaluate(
    () => Boolean(document.querySelector("nav.pasek") && document.querySelector(".znak-slowny")),
  );
  return { kod, tekst, maPowloke };
}

/** Skrót tego, co realnie widać — do wiersza raportu, nie do asercji. */
function coWidac(tekst) {
  const linie = tekst.split("\n").map((l) => l.trim()).filter(Boolean);
  if (!linie.length) return "(pusty ekran)";
  // Pierwsze wiersze to znak słowny i pasek — te same wszędzie. Interesuje
  // nas to, co ekran mówi OD SIEBIE, czyli treść pod nagłówkiem.
  const trescia = linie.slice(11);
  return (trescia.length ? trescia : linie).join(" | ").slice(0, 110);
}

const przegladarka = await chromium.launch();
let kodWyjscia = 0;
try {
  const strona = await przegladarka.newPage({ viewport: { width: 1440, height: 900 } });

  const kluczeZMapy = await licznoscZMapy();
  const wejscie = await strona.goto(`${EKRAN}/`, { waitUntil: "networkidle" });
  if (!wejscie || !wejscie.ok()) {
    console.error(`BŁĄD POMIARU: ekran startowy odpowiedział kodem ${wejscie ? wejscie.status() : "—"}`);
    process.exit(2);
  }

  const wPasku = await strona.evaluate(() =>
    [...document.querySelectorAll("nav.pasek a")].map((a) => a.getAttribute("href")),
  );
  const akcja = await strona.evaluate(() => {
    const a = document.querySelector(".naglowek-wiersz > a.akcja");
    return a ? a.getAttribute("href") : null;
  });

  console.log(`Mapa ekranów mówi: ${kluczeZMapy.length} pozycji paska.`);
  console.log(`Pasek wyrenderował: ${wPasku.length} odsyłaczy${akcja ? " + 1 akcja przy znaku słownym" : ""}.`);

  if (wPasku.length !== kluczeZMapy.length) {
    console.error(
      `BŁĄD POMIARU: pasek oddał ${wPasku.length} odsyłaczy, mapa ekranów ma ${kluczeZMapy.length}. ` +
        "Pomiar na niekompletnym pasku zameldowałby sukces, którego nie ma.",
    );
    process.exit(2);
  }
  if (!akcja) {
    console.error("BŁĄD POMIARU: nie znalazłem akcji przy znaku słownym — nagłówek nie jest tym, co mierzę.");
    process.exit(2);
  }

  const doSprawdzenia = [...wPasku, akcja];
  console.log("");
  for (const adres of doSprawdzenia) {
    const { kod, tekst, maPowloke } = await wejdz(strona, adres);
    const angielskie = ZDANIA_NEXT.find((z) => tekst.includes(z)) ?? null;
    const powody = [];
    if (kod !== 200) powody.push(`kod ${kod}`);
    if (!maPowloke) powody.push("bez powłoki — nie ma czym wyjść");
    if (angielskie) powody.push(`strona wbudowana w Next („${angielskie}")`);
    const werdykt = powody.length ? `NIE PROWADZI — ${powody.join(", ")}` : "prowadzi";
    if (powody.length) kodWyjscia = 1;
    console.log(`${adres.padEnd(16)} ${String(kod).padEnd(4)} ${werdykt}   ⟨${coWidac(tekst)}⟩`);
  }

  // Druga strona: adres, którego mapa nie zna. Ma oddać 404 I polskie zdanie.
  const spoza = await wejdz(strona, ADRES_SPOZA_MAPY);
  const powodySpoza = [];
  if (spoza.kod !== 404) powodySpoza.push(`kod ${spoza.kod}, oczekiwany 404`);
  if (!spoza.maPowloke) powodySpoza.push("bez powłoki");
  const angSpoza = ZDANIA_NEXT.find((z) => spoza.tekst.includes(z)) ?? null;
  if (angSpoza) powodySpoza.push(`strona wbudowana w Next („${angSpoza}")`);
  if (powodySpoza.length) kodWyjscia = 1;
  console.log("");
  console.log(
    `${ADRES_SPOZA_MAPY} ${spoza.kod} ` +
      (powodySpoza.length ? `NIE MÓWI, CO SIĘ STAŁO — ${powodySpoza.join(", ")}` : "mówi po polsku, co się stało") +
      `   ⟨${coWidac(spoza.tekst)}⟩`,
  );

  console.log("");
  console.log(`Sprawdzonych adresów: ${doSprawdzenia.length + 1}`);
  console.log(kodWyjscia === 0 ? "WYNIK: każdy odsyłacz prowadzi." : "WYNIK: któryś odsyłacz nie prowadzi.");
} finally {
  await przegladarka.close();
}
process.exit(kodWyjscia);
