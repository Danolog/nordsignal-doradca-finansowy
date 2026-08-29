// SILNIK WZORCOWY — oddaje ekranom zestaw danych z ramki i NIC WIĘCEJ (D-63).
//
// PO CO. Bramka odwzorowania ma dowodzić, że ekran wygląda jak rysunek.
// Ekrany są komponentami serwerowymi — dane pobiera serwer Next, nie
// przeglądarka — więc żadne podstawienie odpowiedzi po stronie przeglądarki
// tam nie sięga. Jedyne miejsce, w którym da się podmienić źródło, nie
// dotykając ani jednego węzła ekranu, to ADRES SILNIKA. Ten proces staje
// pod tym adresem i mówi ramką.
//
// CO ODDAJE: `GET /api/plynnosc` i `GET /api/ksiegowanie` z wybranego
// zestawu oraz `POST /api/wpisy/podglad` — kartą „Co ruszy ten wpis"
// z ramki Księgowania.
//
// CZEGO NIE ROBI I DLACZEGO GŁOŚNO: `POST /api/wpisy`, `DELETE /api/wpisy/{id}`,
// `PUT /api/kotwica` oraz WSZYSTKIE PIĘĆ ZAPISÓW BUDŻETU (`POST /api/plan`,
// `PUT /api/plan/{id}`, `POST /api/plan/{id}/zakoncz`, `POST /api/plan/kopiuj`,
// `POST /api/cele`) ODMAWIAJĄ zdaniem, zamiast udawać zapis. Wzorzec, który
// pozwala „zapisać", uczyłby, że przebieg odbiorczy przeszedł także po
// stronie danych — a on nie dotknął żadnej bazy. Cztery operacje P-1 dowodzi
// się WYŁĄCZNIE na żywym silniku i żywej bazie, nigdy tutaj.
//
// ILE RZECZY TEN PROCES OBSŁUŻYŁ. Każde żądanie jest liczone, a `SIGTERM`
// i `SIGINT` wypisują licznik na wyjście. Wzorzec, do którego nikt nie
// zadzwonił, wygląda z zewnątrz identycznie jak wzorzec działający —
// a bramka puszczona obok niego mierzy żywe dane i melduje sukces.
//
// Uruchomienie:
//   node narzedzia/silnik-wzorcowy.mjs --zestaw=main --port=8000
//   node narzedzia/silnik-wzorcowy.mjs --zestaw=main-dobrze
// Domyślny port to 8000 — ten sam, pod którym stoi prawdziwy silnik, bo
// `ADRES_SILNIKA` jest czytany raz przy starcie serwera Next. Zamiana
// wzorca na prawdziwy silnik jest wtedy zamianą jednego procesu, a nie
// restartem interfejsu.

import http from "node:http";
import { ZESTAWY } from "./dane-wzorcowe.mjs";

const argumenty = process.argv.slice(2);
const wartosc = (nazwa, domyslna) => {
  const a = argumenty.find((x) => x.startsWith(`--${nazwa}=`));
  return a ? a.slice(nazwa.length + 3) : domyslna;
};

const nazwaZestawu = wartosc("zestaw", "main");
const port = Number(wartosc("port", "8000"));
const zestaw = ZESTAWY[nazwaZestawu];

if (!zestaw) {
  console.error(
    `Nie znam zestawu: ${nazwaZestawu}. Znane: ${Object.keys(ZESTAWY).join(", ")}`,
  );
  process.exit(2);
}

const licznik = new Map();
function policz(klucz) {
  licznik.set(klucz, (licznik.get(klucz) ?? 0) + 1);
}

function oddaj(odpowiedz, kod, tresc) {
  const cialo = JSON.stringify(tresc);
  odpowiedz.writeHead(kod, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(cialo),
  });
  odpowiedz.end(cialo);
}

const ODMOWA =
  "To jest silnik wzorcowy bramki odwzorowania — nie ma bazy i niczego nie zapisuje. " +
  "Uruchom prawdziwy silnik: ./.venv/bin/python -m uvicorn api.index:aplikacja --port 8000.";

const serwer = http.createServer((zadanie, odpowiedz) => {
  const sciezka = new URL(zadanie.url, "http://wzorzec.local").pathname;
  const klucz = `${zadanie.method} ${sciezka}`;
  policz(klucz);

  if (zadanie.method === "GET" && sciezka === "/api/plynnosc") {
    return oddaj(odpowiedz, 200, zestaw.plynnosc);
  }
  if (zadanie.method === "GET" && sciezka === "/api/ksiegowanie") {
    return oddaj(odpowiedz, 200, zestaw.ksiegowanie);
  }
  if (zadanie.method === "GET" && sciezka === "/api/budzet") {
    return oddaj(odpowiedz, 200, zestaw.budzet);
  }
  if (zadanie.method === "POST" && sciezka === "/api/wpisy/podglad") {
    // Karta z ramki, niezależnie od tego, co przyszło w treści żądania:
    // bramka doprowadza formularz do stanu z ramki, więc pytanie jest
    // zawsze to samo. Liczenie czegokolwiek tutaj byłoby drugim nośnikiem
    // reguł budżetu — a te mieszkają w silniku.
    zadanie.resume();
    return oddaj(odpowiedz, 200, zestaw.ksiegowanie.podglad);
  }
  if (sciezka === "/api/zdrowie-wzorca") {
    return oddaj(odpowiedz, 200, {
      zestaw: nazwaZestawu,
      obsluzonych: Object.fromEntries(licznik),
    });
  }
  zadanie.resume();
  return oddaj(odpowiedz, 400, { detail: ODMOWA });
});

function podsumuj(sygnal) {
  const razem = [...licznik.values()].reduce((a, b) => a + b, 0);
  console.log(`\nSilnik wzorcowy „${nazwaZestawu}" kończy (${sygnal}).`);
  console.log(`Obsłużonych żądań: ${razem}`);
  for (const [k, v] of licznik) console.log(`  ${v}× ${k}`);
  if (razem === 0) {
    console.log(
      "UWAGA: zero żądań — nikt do tego wzorca nie zadzwonił. Jeśli w tym czasie " +
        "biegła bramka odwzorowania, mierzyła ŻYWE dane, nie wzorzec.",
    );
  }
  serwer.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 300);
}

process.on("SIGTERM", () => podsumuj("SIGTERM"));
process.on("SIGINT", () => podsumuj("SIGINT"));

serwer.listen(port, "127.0.0.1", () => {
  console.log(`Silnik wzorcowy „${nazwaZestawu}" słucha na http://127.0.0.1:${port}`);
});
