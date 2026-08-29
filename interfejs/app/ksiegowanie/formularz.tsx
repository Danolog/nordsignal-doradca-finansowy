"use client";

// EKRAN KSIEGOWANIE — jedyny ekran, na ktorym uzytkownik COS ROBI.
// Uklad przeniesiony wezel po wezle z `makiety/Ksiegowanie.dc.html`.
//
// TRZY KLIKNIECIA DO ZAPISU, i to jest bramka, nie ambicja:
//   1. wejscie na ekran  -> formularz GOTOWY: data = dzis, typ = Wydatek,
//                           KURSOR JUZ STOI W POLU KWOTY (`autoFocus`),
//   2. kafelek kategorii -> wybor z pasma widocznego, bez rozwijania listy,
//   3. „Zapisz wpis"     -> wpis w bazie.
// Wpisanie kwoty nie kosztuje kliknieca, bo kursor tam stoi — to wlasnie
// `autoFocus` zdejmuje trzecie kliknienie. Usuniecie go lamie bramke.
//
// ZERO KWOT W TYM PLIKU. Kazda liczba przychodzi z `lib/dane/ksiegowanie.ts`
// i jest formatowana przez `lib/kwota.ts`. Pilnuje tego straznik
// `test_ekran_NIE_MA_wpisanej_recznie_kwoty`.
//
// ZERO BRZMIEN W TYM PLIKU. Wszystkie siedem stanow bledu i wszystkie
// etykiety wola `lib/napisy.ts`.
//
// KWOTA JEST NAPISEM OD POCZATKU DO KONCA. Zero `parseFloat`, zero `Number()`
// na jej sciezce — zamiana na liczbe zmiennoprzecinkowa gubi grosze
// (CLAUDE.md §3.1).
//
// PODPIECIE (Z7). Do Z6 `zapisz` konczylo sie wyczyszczeniem pol i NIE UDAWALO,
// ze cokolwiek trafilo do bazy. Od Z7 formularz wola cztery trasy:
// `GET /api/ksiegowanie` (dane wejsciowe, w komponencie serwerowym obok),
// `POST /api/wpisy/podglad` (karta „Co ruszy ten wpis"),
// `POST /api/wpisy` (zapis), `DELETE /api/wpisy/{id}` (wycofanie).
// Uklad nie zmienil sie ani o wezel — zmienilo sie to, skad biora sie liczby.
//
// ZAPIS NIE JEST IDEMPOTENTNY PO STRONIE SILNIKA — dwa zadania daja dwa wpisy
// (zgloszenie Maxa z Z6). Skutek widzi uzytkownik, wiec bramka nalezy do tego
// ekranu: przycisk jest WYLACZONY na czas lotu zadania. To nie jest ozdoba
// interfejsu, tylko jedyna dzisiaj obrona przed podwojnym wydatkiem.

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Powloka } from "../powloka";
import { NAPISY, PROZA, type Czlon } from "@/lib/napisy";
import { sformatujDate, sformatujKwote, sformatujOdczyt } from "@/lib/kwota";
import {
  NAPIS_TYPU,
  TYPY,
  type DaneKsiegowania,
  type Kwota,
  type PodgladSkutku,
  type TypWpisu,
} from "@/lib/kontrakt";
import { pobierzPodglad, wycofajWpis, zapiszWpis } from "@/lib/dane/ksiegowanie";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import s from "./style.module.css";

/* ---------- odczyt tego, co uzytkownik wpisal ---------- */

type OdczytKwoty =
  | { stan: "pusta" }
  | { stan: "nieczytelna" }
  | { stan: "ujemna"; kwota: Kwota }
  | { stan: "ok"; kwota: Kwota };

// Praca WYLACZNIE na napisie: zdejmujemy jednostke i separatory, zamieniamy
// przecinek na kropke i sprawdzamy KSZTALT wyrazeniem regularnym. Nigdzie
// nie powstaje liczba, wiec nie ma gdzie zgubic groszy.
function odczytajKwote(tekst: string): OdczytKwoty {
  const oczyszczony = tekst
    .replace(/zł/gi, "")
    .replace(/[\s ]/g, "")
    .replace(",", ".")
    .trim();
  if (oczyszczony === "") return { stan: "pusta" };
  if (!/^-?\d+(\.\d{1,2})?$/.test(oczyszczony)) return { stan: "nieczytelna" };
  if (oczyszczony.startsWith("-")) return { stan: "ujemna", kwota: oczyszczony.slice(1) };
  return { stan: "ok", kwota: oczyszczony };
}

// Data budowana i czytana W CZASIE POWSZECHNYM (UTC), nigdy lokalnym.
// Zmierzone 2026-08-29: `new Date("2026-10-06T00:00:00")` to czas LOKALNY,
// wiec w strefie letniej Warszawy `getUTCDate()` zwraca 5, nie 6 — i poprawna
// data 6 X 2026 wypadala jako przypadek (a) z §41.5, blokujac KAZDY zapis.
// Brzmienia bledu nie cytujemy nawet w komentarzu: ma JEDEN nosnik
// (`lib/napisy.ts`) i pilnuje tego `test_siedem_brzmien_bledu_MA_JEDEN_nosnik`.
function dataJestCzytelna(iso: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return false;
  const [rok, miesiac, dzien] = iso.split("-");
  const d = new Date(Date.UTC(Number(rok), Number(miesiac) - 1, Number(dzien)));
  return (
    !Number.isNaN(d.getTime()) &&
    d.getUTCFullYear() === Number(rok) &&
    d.getUTCMonth() + 1 === Number(miesiac) &&
    d.getUTCDate() === Number(dzien)
  );
}

/* ---------- znaki rysowane, przeniesione z ramki ---------- */

function Ptaszek() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M3 7.4l2.6 2.6L11 4.4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Strzalka() {
  return (
    <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true">
      <path d="M0 5h12M8.5 1.5L12 5l-3.5 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Daszek() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Plus() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 3.5v9M3.5 8h9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function Proza({ czlony, klasa }: { czlony: readonly Czlon[]; klasa: string }) {
  return (
    <p className={klasa}>
      {czlony.map((c, i) =>
        c.akcent ? (
          <span key={i} className={s.akcent}>
            {c.tekst}
          </span>
        ) : (
          <span key={i}>{c.tekst}</span>
        )
      )}
    </p>
  );
}

// JEDEN NOSNIK ZAMIANY WYJATKU NA ZDANIE DLA CZLOWIEKA.
// `BladWarstwySieciowej` niesie dwa zdania: czego brakuje i co zrobic.
// Wyjatek nieznanego rodzaju NIE dostaje wymyslonego brzmienia — dostaje
// zdanie, ktore mowi wprost, ze to jest nasza wada, a nie brak w danych.
function opisBledu(blad: unknown): string {
  if (blad instanceof BladWarstwySieciowej) return `${blad.czegoBrakuje} ${blad.coZrobic}`;
  return NAPISY.blad.awariaNieznana;
}

/* ---------- ekran ---------- */

export function Formularz({
  poczatkowe,
  dzis,
}: {
  poczatkowe: DaneKsiegowania;
  dzis: string | null;
}) {
  const idKwoty = useId();
  const idSzczegolow = useId();

  // Dane ekranu sa STANEM, nie stala: po zapisie i po wycofaniu przychodza
  // odswiezone w tej samej odpowiedzi (`OdpowiedzZapisu.dane`), bo zmieniaja
  // sie naraz licznik wpisow, lista ostatnich wpisow i kolejnosc kafelkow.
  const [DANE, setDane] = useState<DaneKsiegowania>(poczatkowe);
  const [podglad, setPodglad] = useState<PodgladSkutku>(poczatkowe.podglad);

  const [typ, setTyp] = useState<TypWpisu>(poczatkowe.typDomyslny);
  const [data] = useState(poczatkowe.dzisiaj);
  // Pole kwoty startuje PUSTE. Do Z6 niosło stan pokazowy przepisany z ramki;
  // ramka rysuje formularz w trakcie wypelniania, a nie po wejsciu na ekran.
  const [kwotaTekst, setKwotaTekst] = useState("");
  const [szczegoly, setSzczegoly] = useState("");
  const [kategoria, setKategoria] = useState<string | null>(null);
  const [bladDaty, setBladDaty] = useState<string | null>(null);
  const [bladKwoty, setBladKwoty] = useState<string | null>(null);
  const [pytanieOMinus, setPytanieOMinus] = useState<Kwota | null>(null);
  const [bladKategorii, setBladKategorii] = useState<string | null>(null);
  const [bladTypu, setBladTypu] = useState<string | null>(null);
  const [bladWarstwy, setBladWarstwy] = useState<string | null>(null);
  const [wLocie, setWLocie] = useState(false);

  const odczyt = odczytajKwote(kwotaTekst);
  const podpisPodgladu =
    odczyt.stan === "ok" || odczyt.stan === "ujemna"
      ? sformatujKwote(odczyt.kwota, "neutralna")
      : sformatujKwote(podglad.kwota, "neutralna");

  // KARTA „CO RUSZY TEN WPIS" LICZY SIE W SILNIKU, nie tutaj. Cztery liczby
  // karty sa wynikiem regul budzetu; policzone w przegladarce bylyby drugim
  // nosnikiem tych regul i rozjechalyby sie z zapisem przy pierwszej zmianie.
  //
  // ZWLOKA 300 ms NIE JEST OSZCZEDNOSCIA RUCHU W SIECI, tylko warunkiem
  // prawdziwosci: bez niej „274,06" wysyla piec zapytan, a odpowiedzi wracaja
  // w dowolnej kolejnosci — karta pokazywalaby wtedy skutek kwoty „27,4"
  // po tym, jak uzytkownik dopisal juz koncowke. Licznik `numerZapytania`
  // odrzuca odpowiedzi spoznione; sama zwloka tego nie gwarantuje.
  const numerZapytania = useRef(0);
  const odswiezPodglad = useCallback(
    (kwota: Kwota, wybrana: string) => {
      const moj = ++numerZapytania.current;
      pobierzPodglad({ data, typ, kategoria: wybrana, kwota })
        .then((wynik) => {
          if (moj === numerZapytania.current) setPodglad(wynik);
        })
        .catch((blad: unknown) => {
          if (moj !== numerZapytania.current) return;
          // Karta, ktora nie doliczyla, MOWI o tym — a nie zostaje z liczbami
          // sprzed zmiany, ktore czytaloby sie jako skutek tego wpisu (§3.5).
          setBladWarstwy(opisBledu(blad));
        });
    },
    [data, typ],
  );

  useEffect(() => {
    if (kategoria === null) return;
    if (odczyt.stan !== "ok" && odczyt.stan !== "ujemna") return;
    const kwota = odczyt.kwota;
    const zegar = setTimeout(() => odswiezPodglad(kwota, kategoria), 300);
    return () => clearTimeout(zegar);
    // `odczyt` jest wyliczany przy kazdym rysowaniu, wiec do listy zaleznosci
    // wchodzi jego TRESC, nie obiekt.
  }, [odczyt.stan, odczyt.stan === "ok" || odczyt.stan === "ujemna" ? odczyt.kwota : "",
      kategoria, odswiezPodglad]);

  // Zmiana typu zdejmuje wybor kategorii, bo kategoria nalezy do slownika
  // JEDNEGO typu — zostawiona po przelaczeniu bylaby wyborem z cudzej listy.
  // Pasmo nadal pokazuje slownik wydatkow: kategorie przychodow i oszczednosci
  // przychodza z silnika (`magazyn.wczytaj_kategorie(typ)`) razem z trasami.
  function zmienTyp(nowy: TypWpisu) {
    setTyp(nowy);
    setKategoria(null);
    wyczyscBledy();
  }

  function wyczyscBledy() {
    setBladDaty(null);
    setBladKwoty(null);
    setPytanieOMinus(null);
    setBladKategorii(null);
    setBladTypu(null);
    setBladWarstwy(null);
  }

  // Zapis: siedem stanow z §41.5, kazdy z osobnym brzmieniem. Wspolny
  // komunikat „blad" dla siedmiu przyczyn jest tym samym, co brak komunikatu.
  function zapisz() {
    if (wLocie) return;   // pierwsza obrona przed dubletem — patrz naglowek
    wyczyscBledy();
    let wolno = true;

    if (!TYPY.includes(typ)) {                       // (g) — niemozliwe z konstrukcji
      setBladTypu(NAPISY.blad.typNieznany);
      wolno = false;
    }
    if (!dataJestCzytelna(data)) {                   // (a)
      setBladDaty(NAPISY.blad.dataNieczytelna);
      wolno = false;
    }
    if (odczyt.stan === "pusta") {                   // (b)
      setBladKwoty(NAPISY.blad.kwotaPusta);
      wolno = false;
    }
    if (odczyt.stan === "nieczytelna") {             // (c)
      setBladKwoty(NAPISY.blad.kwotaNieczytelna);
      wolno = false;
    }
    if (odczyt.stan === "ujemna") {                  // (d) — PYTANIE, nie blad
      setPytanieOMinus(odczyt.kwota);
      wolno = false;
    }

    const wybrana = DANE.kategorie.find((k) => k.nazwa === kategoria);
    if (!wybrana) {                                  // (e)
      setBladKategorii(NAPISY.blad.kategoriaNiewybrana);
      wolno = false;
    } else if (!wybrana.aktywna) {                   // (f)
      setBladKategorii(NAPISY.blad.kategoriaNieaktywna(wybrana.nazwa));
      wolno = false;
    }

    if (!wolno) return;
    void przekaz(odczyt.stan === "ok" ? odczyt.kwota : "", false);
  }

  // Po zapisie zostaja data, typ i kategoria; czysci sie kwota i szczegoly.
  //
  // `potwierdzone` niosa DWIE drogi dojscia tutaj: zwykly zapis (falsz)
  // i odpowiedz „Tak, zapisz" na pytanie o minus (prawda). Rozstrzygniecie
  // ma jeden nosnik i jest nim `ekran_ksiegowanie.rozstrzygnij_kwote` —
  // ekran przekazuje odpowiedz uzytkownika, nie podejmuje jej za niego.
  async function przekaz(kwota: Kwota, potwierdzone: boolean) {
    if (wLocie) return;                       // druga obrona przed dubletem
    setWLocie(true);
    try {
      const odp = await zapiszWpis(
        { data, typ, kategoria: kategoria ?? "", kwota, szczegoly },
        { dzis, potwierdzone },
      );
      setDane(odp.dane);
      setPodglad(odp.dane.podglad);
      if (odp.stan === "pytanie_o_minus") {
        setPytanieOMinus(odp.kwota);
        return;
      }
      setKwotaTekst("");
      setSzczegoly("");
    } catch (blad: unknown) {
      setBladWarstwy(opisBledu(blad));
    } finally {
      setWLocie(false);
    }
  }

  // Wycofanie. Brak wiersza o podanym numerze jest BLEDEM po stronie silnika,
  // nie cicha zgoda — i to zdanie dociera tu w calosci, zamiast zamienic sie
  // w znikniecie wiersza bez sladu.
  async function wycofaj(id: number) {
    if (wLocie) return;
    setWLocie(true);
    wyczyscBledy();
    try {
      const odp = await wycofajWpis(id, dzis);
      setDane(odp.dane);
      setPodglad(odp.dane.podglad);
    } catch (blad: unknown) {
      setBladWarstwy(opisBledu(blad));
    } finally {
      setWLocie(false);
    }
  }

  return (
    // `straznik={null}` NIE JEST ZANIEDBANIEM. Stopka odpowiada na pytanie
    // „czy to, co widze, jest aktualne", a odpowiedz na nie niesie WYLACZNIE
    // `DanePlynnosci.ostatnieSprawdzenie`. `DaneKsiegowania` tego pola nie ma,
    // wiec ten ekran go NIE WIE — i mowi „nie wiem" zdaniem z `lib/napisy.ts`,
    // zamiast powtarzac zdanie sprzed podpiecia. Luka kontraktu zgloszona
    // Ethanowi; drugie zapytanie o prognoze tylko dla stopki byloby drugim
    // przebiegiem rachunku dla wyniku, ktorego ten ekran nie pokazuje.
    <Powloka
      aktywny="ksiegowanie"
      odczyt={sformatujOdczyt(DANE.dzisiaj)}
      straznik={null}
    >
      <section className={s.ekran}>

        {/* 1-2. przelacznik typu + data wpisu */}
        <div className={s.sekcjaNaglowka}>
          <div className={s.wierszNaglowka}>
            <span className={s.tytulEkranu}>{NAPISY.tytul}</span>

            <div className={s.przelacznik} role="radiogroup" aria-label={NAPISY.tytul}>
              {TYPY.map((t, i) => (
                <span key={t} style={{ display: "contents" }}>
                  {i > 0 && <span className={s.rozdzielacz} />}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={t === typ}
                    aria-current={t === typ ? "true" : undefined}
                    className={t === typ ? `${s.pozycja} ${s.pozycjaCzynna}` : s.pozycja}
                    onClick={() => zmienTyp(t)}
                  >
                    {t === typ && <Ptaszek />}
                    <span>{NAPIS_TYPU[t]}</span>
                  </button>
                </span>
              ))}
            </div>

            <span className={s.rozpychacz} />
            <span className={s.etykieta}>{NAPISY.etykietaDatyWpisu}</span>
            <button type="button" className={s.kontrolkaDaty}>
              <span className={s.dataSzeryfowa}>{sformatujDate(data)}</span>
              <Daszek />
            </button>
          </div>
          <div className={s.kreska} />
          <div className={s.przerwa} />
          <div className={s.kreska} />
          {bladDaty && (
            <span className={s.podpisUwagi} role="alert">
              {bladDaty}
            </span>
          )}
          {bladTypu && (
            <span className={s.podpisUwagi} role="alert">
              {bladTypu}
            </span>
          )}
        </div>

        {/* 3-5. kwota, podpis o znaku, szczegoly */}
        <div className={s.wierszPol}>
          <div className={s.kolumnaKwoty}>
            <label className={s.etykieta} htmlFor={idKwoty}>
              {NAPISY.etykietaKwoty}
            </label>
            <span className={bladKwoty ? `${s.ramkaKwoty} ${s.uwaga}` : s.ramkaKwoty}>
              <input
                id={idKwoty}
                className={s.wpisKwoty}
                inputMode="decimal"
                autoFocus
                aria-required="true"
                aria-invalid={bladKwoty ? true : undefined}
                value={kwotaTekst}
                onChange={(e) => setKwotaTekst(e.target.value)}
              />
            </span>
            {/* Podpis stoi ZAWSZE, nie tylko po bledzie — po to, zeby blad (d)
                zdarzal sie rzadziej, a nie zeby go tlumaczyc po fakcie.
                Obszar mowiacy (`aria-live`) obejmuje podpis RAZEM z bledami,
                zamiast stac obok pusty: pusty obszar byl by czwartym dzieckiem
                kolumny i dokladal 8 px odstepu, ktorego ramka nie ma. */}
            <div className={s.podKwota} aria-live="polite">
              <span className={s.podpis}>{NAPISY.bezZnaku}</span>
              {bladKwoty && <span className={s.podpisUwagi}>{bladKwoty}</span>}
              {pytanieOMinus && (
                <>
                  <span className={s.podpisUwagi}>
                    {NAPISY.blad.kwotaUjemna(
                      sformatujKwote(pytanieOMinus, "neutralna"),
                      NAPIS_TYPU[typ]
                    )}
                  </span>{" "}
                  <button
                    type="button"
                    className={s.potwierdzenie}
                    onClick={() => {
                      const potwierdzona = pytanieOMinus;
                      setPytanieOMinus(null);
                      void przekaz(potwierdzona, true);
                    }}
                  >
                    {NAPISY.blad.kwotaUjemnaPotwierdzenie}
                  </button>
                </>
              )}
            </div>
          </div>

          <div className={s.kolumnaSzczegolow}>
            <label className={s.etykieta} htmlFor={idSzczegolow}>
              {NAPISY.etykietaSzczegolow}
            </label>
            <span className={s.ramkaSzczegolow}>
              <input
                id={idSzczegolow}
                className={s.wpisSzczegolow}
                value={szczegoly}
                onChange={(e) => setSzczegoly(e.target.value)}
              />
            </span>
          </div>
        </div>

        {/* 6-7. pasmo kategorii + podpis o kolejnosci */}
        <div className={s.sekcjaKategorii}>
          <div className={s.wierszEtykietyKategorii}>
            <span className={s.etykieta}>{NAPISY.etykietaKategorii}</span>
            <span className={s.podpis}>
              {NAPISY.podpisPasma(DANE.kategorie.length, typ)}
            </span>
          </div>
          <div
            className={s.pasmo}
            role="radiogroup"
            aria-label={NAPISY.etykietaKategorii}
            aria-invalid={bladKategorii ? true : undefined}
          >
            {DANE.kategorie.map((k) => {
              const czynny = k.nazwa === kategoria;
              const klasa = [
                s.kafelek,
                czynny ? s.kafelekCzynny : "",
                k.aktywna ? "" : s.kafelekNieaktywny,
                bladKategorii && !czynny ? s.uwaga : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <button
                  key={k.nazwa}
                  type="button"
                  role="radio"
                  aria-checked={czynny}
                  aria-current={czynny ? "true" : undefined}
                  className={klasa}
                  onClick={() => setKategoria(k.nazwa)}
                >
                  {czynny && <Ptaszek />}
                  <span>{k.nazwa}</span>
                </button>
              );
            })}
          </div>
          {/* Ten sam powod co przy kwocie: obszar mowiacy obejmuje podpis
              o kolejnosci, zamiast stac obok pusty. */}
          <div className={s.podPasmem} aria-live="polite">
            {bladKategorii && <span className={s.podpisUwagi}>{bladKategorii}</span>}
            <span className={s.podpis}>{DANE.uzasadnienieKolejnosci}</span>
          </div>
        </div>

        {/* 8-9. zapis + podpis o tym, co po nim zostaje */}
        {/* Wspolny blok, bo `.ekran` ma odstep 24 px miedzy dziecmi: obszar
            mowiacy dolozony jako OSOBNE dziecko dokladal ten odstep nawet
            pusty i przesuwal cala dolna polowe ekranu o 24 px w dol
            (zmierzone bramka odwzorowania: 996 px zamiast 972 px). */}
        <div className={s.blokZapisu}>
        <div className={s.wierszZapisu}>
          <button
            type="button"
            className={s.przyciskZapisz}
            disabled={wLocie}
            aria-busy={wLocie || undefined}
            onClick={zapisz}
          >
            <Plus />
            <span>{NAPISY.zapisz}</span>
          </button>
          <span className={s.podpisZapisu}>
            {NAPISY.coZostajePoZapisie}
            <span className={s.akcent}>{NAPISY.coZostajePoZapisieAkcent}</span>
            {NAPISY.coZostajePoZapisieOgon}
          </span>
        </div>

        {/* AWARIA WARSTWY SIECIOWEJ — zdanie silnika ODDANE W CALOSCI.
            Stoi tu, bo tu stoi ruch, ktory ja wywolal: zapis i wycofanie.
            Obszar mowiacy (`aria-live`) jest ZAWSZE w drzewie, nie pojawia
            sie razem z bledem — obszar dolozony dopiero z trescia bywa
            czytany przez czytniki ekranu z opoznieniem albo wcale. */}
        <div className={s.podZapisem} aria-live="assertive">
          {bladWarstwy && <span className={s.podpisUwagi}>{bladWarstwy}</span>}
        </div>
        </div>

        {/* 10-12. co ruszy ten wpis · czego tu nie ma · ostatnie wpisy */}
        <div className={s.dwieKolumny}>
          <div className={s.kolumna}>
            <div className={s.naglowekBloku}>
              <span className={s.etykieta}>{NAPISY.tytulPodgladu}</span>
              <span className={s.podpis}>{NAPISY.podpisPodgladu(podpisPodgladu)}</span>
            </div>

            {podglad.wiersze.map((w) =>
              w.po === null ? (
                // Czwarty wiersz mowi, co sie NIE ruszylo, i to jest wazniejsze
                // od trzech pierwszych: bez niego Darek szukalby ruchu, ktorego
                // nie ma, i uznalby to za wade obliczen.
                <div key={w.etykieta} className={s.wierszBezZmian}>
                  <span className={s.etykietaWierszaCicha}>{w.etykieta}</span>
                  <span className={s.etykietaWierszaCicha}>{w.wyjasnienie}</span>
                </div>
              ) : (
                <div key={w.etykieta} className={s.wierszSkutku}>
                  <span className={s.etykietaWiersza}>{w.etykieta}</span>
                  <span className={s.liczbaPrzed}>{w.przed}</span>
                  <Strzalka />
                  <span className={s.liczbaPo}>{w.po}</span>
                </div>
              )
            )}

            <div className={s.naglowekBlokuDalszego}>
              <span className={s.etykieta}>{NAPISY.tytulCzegoTuNieMa}</span>
            </div>
            <Proza czlony={PROZA.czegoTuNieMa} klasa={s.proza} />
          </div>

          <div className={s.kolumna}>
            <div className={s.naglowekBloku}>
              <span className={s.etykieta}>{NAPISY.tytulOstatnichWpisow}</span>
              <span className={s.podpis}>
                {NAPISY.licznikWpisow(DANE.liczbaWpisowWMiesiacu, DANE.nazwaMiesiaca)}
              </span>
            </div>

            {DANE.ostatnieWpisy.length === 0 ? (
              <>
                <p className={s.pustaHistoria}>{NAPISY.pustaHistoria}</p>
                <Proza czlony={PROZA.pustaHistoriaPowod} klasa={s.prozaBlisko} />
                <Proza czlony={PROZA.pustaHistoriaHoryzont} klasa={s.prozaBlisko} />
              </>
            ) : (
              <div className={s.listaWpisow}>
                {DANE.ostatnieWpisy.slice(0, 6).map((w) => (
                  <div key={w.id} className={s.wierszWpisu}>
                    <span className={s.etykietaWierszaCicha}>{sformatujDate(w.data)}</span>
                    <span className={s.etykietaWiersza}>{w.kategoria}</span>
                    <span className={s.liczbaPo}>
                      {sformatujKwote(w.kwota, w.typ === "Przychody" ? "dodatnia" : "ujemna")}
                    </span>
                    <button
                      type="button"
                      className={s.wycofaj}
                      disabled={wLocie}
                      onClick={() => void wycofaj(w.id)}
                    >
                      wycofaj
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </section>
    </Powloka>
  );
}
