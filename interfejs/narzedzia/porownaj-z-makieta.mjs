// BRAMKA ODWZOROWANIA — zrzut zbudowanego ekranu wobec zrzutu ramki.
//
// DLACZEGO MASZYNOWO, A NIE OKIEM. Poprzedni projekt ma zmierzoną awarię dokładnie
// tej klasy: raport odbioru ogłosił zgodność „co do piksela", a kontrola obejmowała
// WYŁĄCZNIE pasek nawigacji — treść ekranu była sprzed projektu. Zdanie „zdane" bez
// podanego zakresu jest nieodróżnialne od „zdane w całości". Oko nie umie podać
// zakresu; ta bramka podaje go zawsze: ile pikseli porównała i ile z nich się różni.
//
// DLACZEGO NARZĘDZIE WYPISUJE LICZBĘ PORÓWNANYCH PIKSELI. Sprawdzenie, do którego
// nic nie dociera, melduje sukces. Porównanie dwóch pustych obrazów daje 0,00%
// różnicy tak samo jak porównanie dwóch identycznych ekranów. Dlatego każdy przebieg
// podaje wymiary obu stron i liczbę porównanych pikseli, a przebieg, w którym
// porównanych pikseli jest zero, kończy się kodem 2 (błąd pomiaru), nie kodem 0.
//
// KONTROLA NA WARTOŚCI ZNANEJ — obowiązkowa przed użyciem narzędzia jako dowodu:
//   node narzedzia/porownaj-z-makieta.mjs Ksiegowanie Ksiegowanie   → musi dać 0,00%
//   node narzedzia/porownaj-z-makieta.mjs Ksiegowanie Main          → musi dać >> 2%
// Bez obu tych przebiegów narzędzie może mierzyć własną podłogę.
//
// STAN Z RAMKI (od Z7). Ramka `Ksiegowanie.dc.html` rysuje formularz W TRAKCIE
// WYPEŁNIANIA: kwota wpisana, kategoria wybrana, szczegóły napisane. Po
// podpięciu tras (Z7) ekran wchodzi na scenę PUSTY — bo tak wygląda wejście
// na niego naprawdę — więc porównanie „ramka wobec ekranu po wejściu" mierzy
// RÓŻNICĘ STANU, a nie różnicę układu, i przestaje odpowiadać na pytanie,
// po co ta bramka istnieje.
//
// Dlatego trzeci argument `--stan=<nazwa>` DOPROWADZA EKRAN DO STANU, KTÓRY
// RYSUJE RAMKA, zanim padnie zrzut. Wartości tego stanu (kwota, kategoria,
// szczegóły) są własnością RAMKI, nie aplikacji — i dlatego mieszkają tutaj,
// w narzędziu pomiarowym, a nie w `lib/dane/`, gdzie po Z7 nie ma ani jednej
// kwoty (strażnik `testy/test_dane_bez_kwot.py`).
//
// WZORCOWY ZESTAW DANYCH (od Z7c, D-63). Po podpięciu tras ekran pokazuje
// ŻYWY miesiąc, a ramka rysuje miesiąc, dla którego powstała. Bramka mierzyła
// wtedy naraz układ I dane — zmierzone: `Main` 14,45% przy progu 2%, przy
// układzie, który na danych z ramki dawał 0,00%. Rozstrzygnięcie Sophii:
// ramka bez zmian, ekran dostaje wzorcowy zestaw danych.
//
// Wzorzec podstawia `narzedzia/silnik-wzorcowy.mjs` — proces stojący pod
// adresem silnika. Ekrany są komponentami serwerowymi, więc podmiana
// odpowiedzi po stronie przeglądarki tam nie sięga; adres silnika jest
// jedynym szwem, który nie dotyka ani jednego węzła ekranu.
//
// `--wzorzec` NIE URUCHAMIA wzorca — SPRAWDZA, że ekran na nim stoi.
// Rozdzielenie jest celowe: przebieg puszczony przy przypadkowo działającym
// prawdziwym silniku zmierzyłby pogodę i zameldował wynik, a bramka bez tego
// sprawdzenia nie umiałaby tego odróżnić od sukcesu. Znacznik jest zdaniem,
// które ekran pokazuje WYŁĄCZNIE na wzorcu.
//
// Uruchomienie:
//   node narzedzia/porownaj-z-makieta.mjs Ksiegowanie http://localhost:3000/ksiegowanie
//   node narzedzia/porownaj-z-makieta.mjs Ksiegowanie http://... --stan=ksiegowanie-z-ramki --wzorzec
//   node narzedzia/porownaj-z-makieta.mjs Main http://localhost:3000/ --wzorzec
//   node narzedzia/porownaj-z-makieta.mjs Ksiegowanie Ksiegowanie      (kontrola)
// Drugi argument będący adresem http(s) to zbudowany ekran; każdy inny jest nazwą
// ramki z katalogu `makiety/` (albo ścieżką do pliku .html).
//
// Kody wyjścia: 0 — różnica w progu · 1 — próg przekroczony · 2 — błąd pomiaru.

import { chromium } from "playwright";
import { ZNACZNIK_WZORCA } from "./dane-wzorcowe.mjs";
import path from "node:path";
import fs from "node:fs/promises";
import { pathToFileURL, fileURLToPath } from "node:url";

const PROG = 0.02;          // 2% pikseli — zapas na wygładzanie krojów pisma
const SZEROKOSC = 1440;

// Ile jeden kanał barwy może się różnić, żeby piksel NIE liczył się jako różny.
// Wygładzanie krawędzi liter daje na tych samych literach różnice rzędu kilku
// jednostek; przesunięcie układu daje różnice kilkudziesięciu. Próg oddziela jedno
// od drugiego i celowo jest niski — ma nie przepuścić przesunięcia o pół piksela.
const TOLERANCJA_KANALU = 12;

const KATALOG = path.dirname(fileURLToPath(import.meta.url));
const KORZEN = path.resolve(KATALOG, "..", "..");          // katalog projektu
const KATALOG_RAMEK = path.join(KORZEN, "makiety");
const KATALOG_ZRZUTOW = path.join(KATALOG, "..", "zrzuty");

function adresRamki(nazwa) {
  const sciezka = nazwa.endsWith(".html")
    ? path.resolve(nazwa)
    : path.join(KATALOG_RAMEK, `${nazwa}.dc.html`);
  return { sciezka, url: pathToFileURL(sciezka).href };
}

function jestAdresem(tekst) {
  return /^https?:\/\//i.test(tekst);
}

// Stany, do których wolno doprowadzić ekran przed zrzutem. Każdy opisuje
// dokładnie to, co widać na swojej ramce — ani jednej rzeczy więcej.
const STANY = {
  // `makiety/Ksiegowanie.dc.html`: kwota 274,06 zł w polu, kategoria
  // „Energia Elektryczna" wybrana, szczegóły „prąd, rozliczenie za wrzesień".
  "ksiegowanie-z-ramki": async (strona) => {
    await strona.fill('input[inputmode="decimal"]', "274,06 zł");
    await strona.fill('input:not([inputmode])', "prąd, rozliczenie za wrzesień");
    await strona.click('button[role="radio"]:has-text("Energia Elektryczna")');
    // Karta „Co ruszy ten wpis" dolicza się z trasy; bez tego oczekiwania
    // zrzut złapałby ją sprzed wpisania kwoty i pomiar mierzyłby wyścig.
    await strona.waitForTimeout(900);
  },
};

async function zrzut(przegladarka, url, opis, stan = null) {
  const strona = await przegladarka.newPage({
    viewport: { width: SZEROKOSC, height: 900 },
    deviceScaleFactor: 1,
  });
  const odpowiedz = await strona.goto(url, { waitUntil: "networkidle", timeout: 60_000 });
  if (odpowiedz && !odpowiedz.ok() && jestAdresem(url)) {
    throw new Error(`${opis}: ${url} odpowiedział kodem ${odpowiedz.status()}`);
  }
  // Wygładzanie kroju i obrazy tła potrzebują chwili po `networkidle`.
  await strona.waitForTimeout(400);
  if (stan) await stan(strona);
  const naEkranie = await strona.evaluate(() => document.body.innerText);
  const miara = await strona.evaluate(() => {
    const d = document.documentElement;
    const b = document.body;
    return {
      wysokoscDokumentu: Math.max(b.scrollHeight, b.offsetHeight, d.scrollHeight, d.offsetHeight),
      wezlow: document.querySelectorAll("*").length,
      tekstow: [...document.querySelectorAll("span,p,a,button,div")]
        .filter((e) => e.childElementCount === 0 && e.textContent.trim()).length,
    };
  });
  const bufor = await strona.screenshot({ fullPage: true, animations: "disabled" });
  await strona.close();
  return { bufor, miara, naEkranie };
}

// Porównanie idzie w przeglądarce, bo tylko ona umie zdekodować PNG bez dokładania
// zależności. Obie strony trafiają na płótna o tej samej wysokości (większej z dwóch),
// tło białe — więc różnica wysokości JEST różnicą, a nie cichym obcięciem.
async function porownaj(przegladarka, buforA, buforB) {
  const strona = await przegladarka.newPage({ viewport: { width: 400, height: 200 } });
  await strona.route("https://zrzut.local/**", async (trasa) => {
    const nazwa = new URL(trasa.request().url()).pathname;
    if (nazwa === "/a.png") return trasa.fulfill({ contentType: "image/png", body: buforA });
    if (nazwa === "/b.png") return trasa.fulfill({ contentType: "image/png", body: buforB });
    return trasa.fulfill({ contentType: "text/html", body: "<!doctype html><title>porownanie</title>" });
  });
  await strona.goto("https://zrzut.local/pusta");

  const wynik = await strona.evaluate(async (tolerancja) => {
    const wczytaj = (adres) =>
      new Promise((gotowe, blad) => {
        const obraz = new Image();
        obraz.onload = () => gotowe(obraz);
        obraz.onerror = () => blad(new Error(`nie udało się zdekodować ${adres}`));
        obraz.src = adres;
      });

    const a = await wczytaj("https://zrzut.local/a.png");
    const b = await wczytaj("https://zrzut.local/b.png");

    const szerokosc = Math.max(a.naturalWidth, b.naturalWidth);
    const wysokosc = Math.max(a.naturalHeight, b.naturalHeight);
    if (szerokosc === 0 || wysokosc === 0) {
      return { blad: "jedna ze stron ma zerowy wymiar" };
    }

    const naPlotno = (obraz) => {
      const p = document.createElement("canvas");
      p.width = szerokosc;
      p.height = wysokosc;
      const k = p.getContext("2d", { willReadFrequently: true });
      k.fillStyle = "#ffffff";
      k.fillRect(0, 0, szerokosc, wysokosc);
      k.drawImage(obraz, 0, 0);
      return k.getImageData(0, 0, szerokosc, wysokosc).data;
    };

    const pa = naPlotno(a);
    const pb = naPlotno(b);

    const plotnoRoznicy = document.createElement("canvas");
    plotnoRoznicy.width = szerokosc;
    plotnoRoznicy.height = wysokosc;
    const kontekstRoznicy = plotnoRoznicy.getContext("2d");
    const maska = kontekstRoznicy.createImageData(szerokosc, wysokosc);

    let porownanych = 0;
    let roznych = 0;
    let najwiekszaRoznica = 0;

    for (let i = 0; i < pa.length; i += 4) {
      porownanych += 1;
      const dr = Math.abs(pa[i] - pb[i]);
      const dg = Math.abs(pa[i + 1] - pb[i + 1]);
      const db = Math.abs(pa[i + 2] - pb[i + 2]);
      const d = Math.max(dr, dg, db);
      if (d > najwiekszaRoznica) najwiekszaRoznica = d;
      const rozny = d > tolerancja;
      if (rozny) roznych += 1;
      // maska: różnica na czerwono, zgodność wyblakłym oryginałem
      maska.data[i] = rozny ? 255 : 235;
      maska.data[i + 1] = rozny ? 40 : 235;
      maska.data[i + 2] = rozny ? 40 : 235;
      maska.data[i + 3] = 255;
    }
    kontekstRoznicy.putImageData(maska, 0, 0);

    return {
      szerokosc,
      wysokosc,
      wymiarA: [a.naturalWidth, a.naturalHeight],
      wymiarB: [b.naturalWidth, b.naturalHeight],
      porownanych,
      roznych,
      najwiekszaRoznica,
      maskaPng: plotnoRoznicy.toDataURL("image/png"),
    };
  }, TOLERANCJA_KANALU);

  await strona.close();
  return wynik;
}

function procent(ulamek) {
  return `${(ulamek * 100).toFixed(2).replace(".", ",")}%`;
}

async function glowna() {
  const argumenty = process.argv.slice(2);
  const nazwaStanu = (argumenty.find((a) => a.startsWith("--stan=")) ?? "").slice("--stan=".length);
  const zadanyWzorzec = argumenty.includes("--wzorzec");
  const [nazwaRamki, cel] = argumenty.filter((a) => !a.startsWith("--"));
  if (nazwaStanu && !STANY[nazwaStanu]) {
    console.error(`Nie znam stanu: ${nazwaStanu}. Znane: ${Object.keys(STANY).join(", ")}`);
    process.exit(2);
  }
  if (!nazwaRamki || !cel) {
    console.error("Użycie: node narzedzia/porownaj-z-makieta.mjs <NazwaRamki> <adres-ekranu | NazwaRamki>");
    process.exit(2);
  }

  const ramka = adresRamki(nazwaRamki);
  try {
    await fs.access(ramka.sciezka);
  } catch {
    console.error(`Nie ma ramki: ${ramka.sciezka}`);
    process.exit(2);
  }

  const drugaStrona = jestAdresem(cel)
    ? { url: cel, opis: `ekran ${cel}`, plik: null }
    : (() => {
        const r = adresRamki(cel);
        return { url: r.url, opis: `ramka ${cel}`, plik: r.sciezka };
      })();

  if (drugaStrona.plik) {
    try {
      await fs.access(drugaStrona.plik);
    } catch {
      console.error(`Nie ma ramki: ${drugaStrona.plik}`);
      process.exit(2);
    }
  }

  const trybKontroli = drugaStrona.plik === ramka.sciezka;

  await fs.mkdir(KATALOG_ZRZUTOW, { recursive: true });
  const przegladarka = await chromium.launch();
  let kod = 0;
  try {
    const a = await zrzut(przegladarka, ramka.url, `ramka ${nazwaRamki}`);
    const b = await zrzut(przegladarka, drugaStrona.url, drugaStrona.opis,
      nazwaStanu && !drugaStrona.plik ? STANY[nazwaStanu] : null);

    // SPRAWDZENIE, NA CZYM STOI EKRAN — przed pomiarem, nie po nim.
    // Bez niego przebieg wobec żywego silnika jest nieodróżnialny od
    // przebiegu wobec wzorca: oba kończą się liczbą procent.
    if (zadanyWzorzec) {
      if (drugaStrona.plik) {
        console.error("BŁĄD POMIARU: --wzorzec ma sens tylko wobec zbudowanego ekranu, nie wobec ramki.");
        process.exit(2);
      }
      if (!b.naEkranie.includes(ZNACZNIK_WZORCA)) {
        console.error(
          "BŁĄD POMIARU: ekran NIE stoi na wzorcowym zestawie danych — nie widzę znacznika:\n" +
            `  „${ZNACZNIK_WZORCA}"\n` +
            "Uruchom wzorzec pod adresem silnika:\n" +
            "  node narzedzia/silnik-wzorcowy.mjs --zestaw=<main|main-dobrze|ksiegowanie> --port=8000",
        );
        process.exit(2);
      }
    }

    const plikA = path.join(KATALOG_ZRZUTOW, `${nazwaRamki}-ramka.png`);
    const plikB = path.join(KATALOG_ZRZUTOW, `${nazwaRamki}-${trybKontroli ? "kontrola" : "ekran"}.png`);
    await fs.writeFile(plikA, a.bufor);
    await fs.writeFile(plikB, b.bufor);

    const wynik = await porownaj(przegladarka, a.bufor, b.bufor);
    if (wynik.blad) {
      console.error(`BŁĄD POMIARU: ${wynik.blad}`);
      process.exit(2);
    }
    if (wynik.porownanych === 0) {
      console.error("BŁĄD POMIARU: porównano zero pikseli — pomiar nic nie widział.");
      process.exit(2);
    }

    const plikRoznicy = path.join(KATALOG_ZRZUTOW, `${nazwaRamki}-roznica.png`);
    await fs.writeFile(plikRoznicy, Buffer.from(wynik.maskaPng.split(",")[1], "base64"));

    const udzial = wynik.roznych / wynik.porownanych;

    console.log(`Ramka:  ${nazwaRamki}  ${wynik.wymiarA[0]}x${wynik.wymiarA[1]} px · ${a.miara.wezlow} węzłów · ${a.miara.tekstow} tekstów`);
    console.log(`Druga strona: ${drugaStrona.opis}  ${wynik.wymiarB[0]}x${wynik.wymiarB[1]} px · ${b.miara.wezlow} węzłów · ${b.miara.tekstow} tekstów`);
    if (trybKontroli) console.log("TRYB KONTROLI — obie strony to ten sam plik; oczekiwana różnica 0,00%.");
    if (nazwaStanu) console.log(`Stan ekranu przed zrzutem: ${nazwaStanu}`);
    if (zadanyWzorzec) console.log("Źródło danych ekranu: WZORZEC (znacznik znaleziony na ekranie).");
    console.log(`Pole porównania: ${wynik.szerokosc}x${wynik.wysokosc} px`);
    console.log(`Porównanych pikseli: ${wynik.porownanych}`);
    console.log(`Różniących się:      ${wynik.roznych}  (tolerancja kanału ${TOLERANCJA_KANALU}, największa zmierzona różnica kanału ${wynik.najwiekszaRoznica})`);
    console.log(`RÓŻNICA: ${procent(udzial)}   PRÓG: ${procent(PROG)}`);
    console.log(`Zrzuty: ${plikA}`);
    console.log(`        ${plikB}`);
    console.log(`        ${plikRoznicy}`);

    if (udzial > PROG) {
      console.log("WYNIK: PRÓG PRZEKROCZONY — wracasz do układu, nie do progu.");
      kod = 1;
    } else {
      console.log("WYNIK: w progu.");
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
