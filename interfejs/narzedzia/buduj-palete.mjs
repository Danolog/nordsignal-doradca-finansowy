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
const cel = join(tu, "..", "app", "paleta.css");

const paleta = JSON.parse(readFileSync(zrodlo, "utf8"));

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
}

[data-motyw="ciemny"] {
${blok(paleta.ciemny)}
}
`;

writeFileSync(cel, css, "utf8");
console.log(
  `paleta.css zapisana: ${paleta.jasny.length} rol jasnych, ` +
  `${paleta.ciemny.length} ciemnych, wersja ${paleta.wersja}`
);
