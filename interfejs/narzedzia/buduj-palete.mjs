// Generuje `interfejs/app/paleta.css` z `makiety/paleta.json`.
//
// DLACZEGO GENERATOR, A NIE RECZNE PRZEPISANIE. Paleta ma JEDEN NOSNIK
// (`makiety/paleta.json`) i jest wiazaca specyfikacja wygladu. Recznie
// przepisany arkusz stylow bylby drugim nosnikiem — a barwa rozjechana
// o jeden ton wobec ramki lamie bramke odwzorowania (PRD §12.7), przy czym
// nikt tego nie zauwazy, bo oba pliki wygladaja na zadbane.
//
// Uruchamiaj przed budowaniem: `node narzedzia/buduj-palete.mjs`.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const tu = dirname(fileURLToPath(import.meta.url));
const zrodlo = join(tu, "..", "..", "makiety", "paleta.json");
const zrodloFaktury = join(tu, "..", "..", "makiety", "Ksiegowanie.dc.html");
const cel = join(tu, "..", "app", "paleta.css");

const paleta = JSON.parse(readFileSync(zrodlo, "utf8"));

// FAKTURA ARKUSZA — czterowarstwowy szum SVG. Jej NOSNIKIEM jest ramka, bo
// ramka jest wiazaca specyfikacja wygladu (CLAUDE.md §3.6), a bramka
// odwzorowania porownuje z nia zrzut piksel po pikselu. Przepisanie tego
// obrazu recznie do arkusza stylow byloby drugim nosnikiem tekstury —
// rozjazd o jeden ziarnisty parametr lamalby bramke, a oba pliki
// wygladalyby na zadbane. Dlatego generator go STAMTAD WYCINA.
// `paleta.json` niesie same barwy wlokna (`faktura.wlokno_*`) i sluzy tu
// za kontrole: jesli wyciety obraz ich nie zawiera, generator pada.
const ramka = readFileSync(zrodloFaktury, "utf8");
const trafienie = ramka.match(/background-image: (url\('data:image\/svg\+xml,[^']*'\));/);
if (!trafienie) {
  throw new Error(`nie znalazlem faktury arkusza w ${zrodloFaktury}`);
}
const faktura = trafienie[1];
for (const barwa of [paleta.faktura.wlokno_ciemne, paleta.faktura.wlokno_jasne]) {
  const wKodzieUrl = "%23" + barwa.slice(1);
  if (!faktura.includes(wKodzieUrl)) {
    throw new Error(`faktura z ramki nie niesie barwy wlokna ${barwa} — paleta i ramka sie rozjechaly`);
  }
}

const nazwa = (rola) =>
  "--" + rola.normalize("NFD").replace(/[̀-ͯ]/g, "")
             .replace(/\s+/g, "-").toLowerCase();

const blok = (role, wciecie = "  ") =>
  role.map((r) => `${wciecie}${nazwa(r.rola)}: ${r.final};`).join("\n");

const css = `/* WYGENEROWANE z makiety/paleta.json (wersja ${paleta.wersja}, ${paleta.data}).
   NIE EDYTUJ RECZNIE — zmiana ginie przy najblizszym przebiegu generatora.
   Zrodlem barwy jest paleta.json; ten plik ja WOLA. */

:root {
${blok(paleta.jasny)}
  --faktura-arkusza: ${faktura};
}

[data-motyw="ciemny"] {
${blok(paleta.ciemny)}
}
`;

writeFileSync(cel, css, "utf8");
console.log(
  `paleta.css zapisana: ${paleta.jasny.length} rol jasnych, ` +
  `${paleta.ciemny.length} ciemnych, faktura ${faktura.length} znakow, ` +
  `wersja ${paleta.wersja}`
);
