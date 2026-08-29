"use client";

// KONTROLKA STANU KONTA — pozycja 1 z osmiu pierwszego uruchomienia (W8).
//
// PO CO ISTNIEJE. Do W8 cala warstwa pod spodem byla gotowa i NIKT jej nie
// wolal: trasa `PUT /api/kotwica` stala, `zapiszKotwice` bylo napisane i mialo
// zero wolajacych (zmierzone: `grep -rn "zapiszKotwice" interfejs/` = jedno
// trafienie, sama definicja). Skutek widzial uzytkownik: `GET /api/plynnosc`
// oddawal `saldoMinimalne: null`, a ekran zdanie „Nie policze prognozy: nie
// wiem, ile masz na koncie" — bez zadnego miejsca, w ktorym da sie to podac.
//
// CO RYSUJE RAMKA, A CO NIE — nazwane, bo §3.6 czyni makiete wiazaca.
// `makiety/NieWiem.dc.html` rysuje WEZWANIE: przycisk „Podaj stan konta"
// i zdanie „To jedna liczba i jedna data — reszta policzy sie sama".
// `makiety/TrzyStany.dc.html` rysuje jego drugie brzmienie („Odswiez stan
// konta") dla odczytu, ktory sie zestarzal. SAMEGO POLA WPISYWANIA NIE
// RYSUJE ZADNA RAMKA — zmierzone przeszukaniem wszystkich 49 ramek katalogu
// `makiety` wzorcem „<input" i „<form": zero trafien. Pilnuje tego straznik
// `testy/test_ekran_plynnosc.py::test_ZADNA_ramka_NIE_RYSUJE_pola_wpisywania`,
// ktory zaczerwieni sie w dniu, w ktorym taka ramka powstanie. Rozwiniecie ponizej jest wiec ODSTEPSTWEM zgloszonym
// w raporcie W8, a nie milczaca decyzja wykonawcy.
//
// TRZY DOTKNIECIA DO ZAPISU — bramka, nie ambicja (ryzyko R2 z PRD: poprzedni
// arkusz Darka stanal 4 XII 2025 i milczy od 266 dni; recznie wpisywanie
// zamiera, gdy kosztuje wiecej niz trzy dotkniecia):
//   1. „Podaj stan konta"  -> rozwiniecie, KURSOR JUZ STOI w polu kwoty,
//   2. wpisanie kwoty      -> nie kosztuje dotkniecia (`autoFocus`),
//   3. „Zapisz stan konta" -> albo Enter w polu kwoty, czyli zero dotkniec.
// Data jest WYPELNIONA dniem, dla ktorego silnik policzyl ekran — typowy
// przypadek („liczba z dzisiaj") nie kosztuje ani jednego dotkniecia wiecej.
// Usuniecie `autoFocus` albo wartosci domyslnej daty lamie bramke.
//
// KWOTA JEST NAPISEM OD POCZATKU DO KONCA. Zero `parseFloat`, zero `Number()`
// na jej sciezce; ksztalt sprawdza `odczytajKwote` z `lib/kwota.ts` — jeden
// nosnik wspolny z Ksiegowaniem (CLAUDE.md §3.1, §3.2).
//
// MINUS JEST TU DOZWOLONY I TO JEST JEDYNE TAKIE MIEJSCE W APLIKACJI.
// Konto na debecie to realny stan konta, nie blad wpisu. Ksiegowanie pyta
// o minus („kierunek niesie typ wpisu"), stan konta przyjmuje go bez pytania —
// nosnikiem tej roznicy jest `silnik/rdzen/magazyn.py::zapisz_stan_konta`.
//
// ZAPIS ODDAJE CALY EKRAN, nie „zapisano". Nowy odczyt przesuwa punkt startu
// prognozy, wiec zmienia NARAZ werdykt, dzien pod kreska, saldo minimalne
// i cala serie. Dlatego ta kontrolka nie odswieza strony i nie odpytuje
// drugi raz — oddaje rodzicowi `DanePlynnosci` z odpowiedzi `PUT`.

import { useId, useRef, useState } from "react";
import { dataJestCzytelna, odczytajKwote, sformatujOdczyt } from "@/lib/kwota";
import { NAPISY_KOTWICY } from "@/lib/napisy";
import type { DanePlynnosci } from "@/lib/kontrakt";
import { zapiszKotwice } from "@/lib/dane/plynnosc";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import s from "./style.module.css";

// JEDEN NOSNIK ZAMIANY WYJATKU NA ZDANIE DLA CZLOWIEKA — jak w Ksiegowaniu.
// Wyjatek nieznanego rodzaju NIE dostaje wymyslonego brzmienia (§3.7).
function opisBledu(blad: unknown): string {
  if (blad instanceof BladWarstwySieciowej) return `${blad.czegoBrakuje} ${blad.coZrobic}`;
  return NAPISY_KOTWICY.kwotaNieczytelna;
}

export function Kotwica({
  DANE,
  dzis,
  otwarta,
  ustawOtwarta,
  poZapisie,
}: {
  DANE: DanePlynnosci;
  dzis: string | null;
  otwarta: boolean;
  ustawOtwarta: (otwarta: boolean) => void;
  poZapisie: (dane: DanePlynnosci) => void;
}) {
  const idKwoty = useId();
  const idDaty = useId();

  const [kwotaTekst, setKwotaTekst] = useState("");
  // Data startuje dniem, DLA KTOREGO silnik policzyl ten ekran — nie
  // `new Date()` w przegladarce. Zegar przegladarki bylby drugim nosnikiem
  // odpowiedzi na pytanie „ktory dzis", a przy pomiarze odbiorczym
  // (`?dzis=…`) mowilby co innego niz liczby obok.
  const [dataTekst, setDataTekst] = useState(DANE.odczyt);
  const [bladKwoty, setBladKwoty] = useState<string | null>(null);
  const [bladDaty, setBladDaty] = useState<string | null>(null);
  const [bladWarstwy, setBladWarstwy] = useState<string | null>(null);

  // ZAMEK NA `useRef`, NIE NA STANIE — naprawa z Z7c powtorzona tutaj
  // swiadomie. Stan dociera do funkcji obslugi dopiero przy NASTEPNYM
  // rysowaniu, wiec trzy klikniecia w jednym zadaniu przegladarki czytaja
  // trzy razy `false`. Sam zapis jest po stronie silnika idempotentny
  // (`ON CONFLICT(data) DO UPDATE`), wiec zamek nie broni przed dubletem
  // w bazie — broni przed WYSCIGIEM ODPOWIEDZI: druga odpowiedz potrafi
  // wrocic pierwsza i ekran pokazalby wtedy prognoze sprzed poprawki.
  const zamek = useRef(false);
  const [wLocie, setWLocie] = useState(false);

  // Wezwanie ma DWA brzmienia i rozstrzyga o nich obecnosc odczytu, a nie
  // wyglad: bez kotwicy „Podaj", z kotwica „Odswiez".
  const maKotwice = DANE.saldoMinimalne !== null;

  function zamknij() {
    ustawOtwarta(false);
    setBladKwoty(null);
    setBladDaty(null);
    setBladWarstwy(null);
  }

  async function zapisz() {
    if (zamek.current) return;
    setBladKwoty(null);
    setBladDaty(null);
    setBladWarstwy(null);

    const odczyt = odczytajKwote(kwotaTekst);
    let wolno = true;
    if (odczyt.stan === "pusta") {
      setBladKwoty(NAPISY_KOTWICY.kwotaPusta);
      wolno = false;
    }
    if (odczyt.stan === "nieczytelna") {
      setBladKwoty(NAPISY_KOTWICY.kwotaNieczytelna);
      wolno = false;
    }
    if (!dataJestCzytelna(dataTekst)) {
      setBladDaty(NAPISY_KOTWICY.dataNieczytelna);
      wolno = false;
    }
    if (!wolno || (odczyt.stan !== "ok" && odczyt.stan !== "ujemna")) return;

    // Znak SKLADANY Z NAPISU, nigdy z liczby. `odczytajKwote` oddaje kwote
    // bez znaku, a kierunek w polu `stan` — tutaj wraca minus, bo dla stanu
    // konta znak jest czescia odczytu, a nie pomylka jezyka.
    const kwota = odczyt.stan === "ujemna" ? `-${odczyt.kwota}` : odczyt.kwota;

    zamek.current = true;
    setWLocie(true);
    try {
      const dane = await zapiszKotwice({ data: dataTekst, kwota }, dzis);
      poZapisie(dane);
      setKwotaTekst("");
      ustawOtwarta(false);
    } catch (blad: unknown) {
      // Awaria do stanu uzytecznego, nie do zera (§3.7): kontrolka ZOSTAJE
      // otwarta z tym, co czlowiek wpisal, i mowi, czego brakuje i co zrobic.
      // Zamkniecie jej po bledzie kazaloby wpisywac kwote drugi raz.
      setBladWarstwy(opisBledu(blad));
    } finally {
      zamek.current = false;
      setWLocie(false);
    }
  }

  // SPOCZYNEK MA DWA KSZTALTY I ROZSTRZYGA O NICH RAMKA, NIE WYGODA.
  //
  // BEZ ODCZYTU rysujemy wezwanie dokladnie tak, jak `NieWiem.dc.html`:
  // wypelniony przycisk i zdanie obok. W tym stanie na ekranie nie ma ani
  // jednej liczby, wiec nie ma czym pokazac pierwszenstwa poza ta kontrolka.
  //
  // Z ODCZYTEM nie rysujemy TU NICZEGO — i to jest decyzja z pomiarem, nie
  // przeoczenie. `Main.dc.html` (ten sam ekran, stan „wiem") nie ma zadnego
  // przycisku, a doklejony miedzy werdyktem a karta zepchnal ekran o 80 px
  // w dol: ZMIERZONE 2026-08-29, odwzorowanie ramki 14,38% przy progu 2%
  // i przy 0,07% przed zmiana. Wejsciem do zmiany odczytu jest wtedy sam
  // DOPISEK przy wierszu otwarcia („z odczytu 9 920,79 zl z 1 wrzesnia") —
  // kontrolka stoi przy liczbie, ktora zmienia, i nie kosztuje ani jednego
  // piksela (CLAUDE.md §3.5).
  //
  // CZEGO PRZEZ TO NIE MA: osobnego, widocznego wezwania „Odswiez stan konta"
  // z `TrzyStany.dc.html`. Tamta ramka rysuje je dla stanu „wiem, ale
  // nieaktualne", a interfejs dzis tego stanu NIE ROZPOZNAJE maszynowo:
  // silnik dokleja zdanie „Odswiez stan konta." do `zdanieWerdyktu`
  // (`silnik/ekran_plynnosc.py`, kod `kotwica_nieaktualna`), ale kontrakt nie
  // niesie osobnego pola. Rozpoznawanie stanu po TRESCI zdania byloby drugim
  // nosnikiem reguly swiezosci. Dlug zgloszony w raporcie W8; prog: pole
  // stanu kotwicy w `DanePlynnosci`.
  if (!otwarta) {
    if (maKotwice) return null;
    return (
      <div className={s.blokKotwicy}>
        <div className={s.wierszKotwicy}>
          <button
            type="button"
            className={`${s.wezwanieKotwicyMocne} ${s.przycisk}`}
            onClick={() => ustawOtwarta(true)}
          >
            {NAPISY_KOTWICY.podaj}
          </button>
          <span className={s.obietnica}>{NAPISY_KOTWICY.obietnica}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={s.blokKotwicy}>
      <div className={s.wierszPolKotwicy}>
        <div className={s.kolumnaKwotyKotwicy}>
          <label className={s.etykietaSekcji} htmlFor={idKwoty}>
            {NAPISY_KOTWICY.etykietaKwoty}
          </label>
          <span className={s.ramkaKwotyKotwicy}>
            <input
              id={idKwoty}
              className={s.wpisKwotyKotwicy}
              inputMode="decimal"
              autoFocus
              value={kwotaTekst}
              onChange={(e) => setKwotaTekst(e.target.value)}
              onKeyDown={(e) => {
                // Enter zdejmuje trzecie dotkniecie. Bez niego zapis kosztuje
                // klik w przycisk, czyli o jedno wiecej niz obiecuje zdanie
                // „To jedna liczba i jedna data".
                if (e.key === "Enter") void zapisz();
                if (e.key === "Escape") zamknij();
              }}
              aria-describedby={`${idKwoty}-podpis`}
            />
            <span className={s.jednostkaKotwicy}>zł</span>
          </span>
          <span className={s.podpis} id={`${idKwoty}-podpis`}>
            {NAPISY_KOTWICY.zeZnakiem}
          </span>
          {bladKwoty && (
            <span className={s.podpisUwagi} role="alert">
              {bladKwoty}
            </span>
          )}
        </div>

        <div className={s.kolumnaDatyKotwicy}>
          <label className={s.etykietaSekcji} htmlFor={idDaty}>
            {NAPISY_KOTWICY.etykietaDaty}
          </label>
          <input
            id={idDaty}
            type="date"
            className={`${s.wpisDatyKotwicy} ${s.przycisk}`}
            value={dataTekst}
            onChange={(e) => setDataTekst(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void zapisz();
              if (e.key === "Escape") zamknij();
            }}
          />
          {/* DATA POWTORZONA PO POLSKU — i to nie jest ozdoba. Pole `type="date"`
              rysuje sobie przegladarka WEDLUG USTAWIEN SYSTEMU: zmierzone
              2026-08-29 na tym laptopie, data 2 wrzesnia 2026 pokazala sie
              jako „09/02/2026", czyli w zapisie, ktory po polsku czyta sie
              jako 9 LUTEGO. Pomylka o siedem miesiecy przesuwa punkt startu
              calej prognozy i nie zostawia po sobie zadnego sladu.
              Zdanie nizej mowi te sama date slowami — wola `sformatujOdczyt`,
              ten sam nosnik, ktorego uzywa naglowek ekranu (§3.5). */}
          {dataJestCzytelna(dataTekst) && (
            <span className={s.podpis}>{sformatujOdczyt(dataTekst)}</span>
          )}
          {bladDaty && (
            <span className={s.podpisUwagi} role="alert">
              {bladDaty}
            </span>
          )}
        </div>

        <div className={s.kolumnaZapisuKotwicy}>
          <button
            type="button"
            className={`${s.wezwanieKotwicyMocne} ${s.przycisk}`}
            onClick={() => void zapisz()}
            disabled={wLocie}
            aria-busy={wLocie}
          >
            {NAPISY_KOTWICY.zapisz}
          </button>
          <button type="button" className={s.rezygnuje} onClick={zamknij}>
            {NAPISY_KOTWICY.rezygnuje}
          </button>
        </div>
      </div>

      {bladWarstwy && (
        <span className={s.podpisUwagi} role="alert">
          {bladWarstwy}
        </span>
      )}
    </div>
  );
}
