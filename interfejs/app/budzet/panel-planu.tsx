"use client";

// PANEL POZYCJI PLANU — JEDNA KONTROLKA W DWOCH TRYBACH (W9c).
//
// PO CO ISTNIEJE. Ekran Budzet ma szesc tras; dwie z nich — `PUT /api/plan/{id}`
// i `POST /api/plan/{id}/zakoncz` — NIE MAJA ZADNEGO ELEMENTU NA RAMCE.
// Sprawdzone trzykrotnie przez Mile: wiersze kategorii w tabeli „Plan kontra
// wykonanie" to gole `<span>`, a jedyny „kosz" na ramce stoi w sekcji Historia
// i dotyczy transakcji, nie planu. To jest DOKLADNIE ta klasa wady, ktora
// zlapal W8 po drugiej stronie: warstwa gotowa, funkcja napisana, zero
// wolajacych — i czlowiek bez miejsca, w ktorym da sie ja uruchomic.
//
// ODSTEPSTWO OD §3.6, ZGLOSZONE, NIE MILCZACE. Rozstrzygniecie Mili
// (`docs/2026-08-29-spis-ekran-budzet.md` §4): nazwa kategorii w tabeli staje
// sie kontrolka i otwiera TEN SAM panel co „Dodaj pozycję planu", w trybie
// zmiany; koniec reguly stoi wewnatrz panelu. Jeden komponent, dwa tryby —
// nie nowy typ wiersza z ikonami w siatce `210px 130px 1fr 130px 190px`,
// ktora nie ma miejsca na dodatkowa kolumne.
// PROG: ramka Budzetu przy najblizszej edycji dostaje te dwa elementy.
// Straznik: `testy/test_ekran_budzet.py::
// test_ramka_Budzetu_NIE_RYSUJE_kontrolki_zmiany_ani_konca_reguly`.
//
// KOSZ KONCZY REGULE, NIE KASUJE — i widac to w trzech miejscach naraz:
// w napisie („Zakończ tę pozycję od października 2026", nigdy „Usuń"),
// w zdaniu potwierdzenia („Wcześniejsze miesiące zostają bez zmian…")
// i w metodzie zadania (`POST .../zakoncz`, nigdy `DELETE`). Pazdziernik
// i listopad maja nadal pokazywac, ze pozycja byla zaplanowana i ile z niej
// wykonano; zmienia sie wylacznie przyszlosc.
//
// TOZSAMOSC POZYCJI JEST NIERUCHOMA W TRYBIE ZMIANY i mowi o tym ZDANIE,
// nie milczenie. Silnik bierze typ, kategorie i opis z wiersza wskazanego
// numerem (`ekran_budzet.zmien_pozycje`) — zmiana kategorii ta droga nie
// bylaby poprawka tej samej pozycji, tylko podmiana jednej na inna, a
// wykonanie policzone juz w starej kategorii zostaloby przy niej.
//
// KWOTA JEST NAPISEM OD POLA DO BAZY. Zero `parseFloat`, zero `Number()` na
// jej sciezce; ksztalt sprawdza `odczytajKwote` z `lib/kwota.ts` — jeden
// nosnik wspolny z Ksiegowaniem i z kontrolka stanu konta (§3.1, §3.2).
// `Number()` pada w tym pliku wylacznie na DNIU MIESIACA i CYKLU, czyli na
// licznikach, w ktorych nie ma groszy do zgubienia.
//
// ZAPIS ODDAJE CALY EKRAN, nie „zapisano". Jedna zmiana planu rusza naraz
// trzy kafelki, bilans, tabele i licznik naglowka — dlatego panel nie
// odswieza strony i nie odpytuje drugi raz, tylko oddaje rodzicowi
// `DaneBudzetu` z odpowiedzi.

import { useId, useRef, useState } from "react";
import { odczytajKwote } from "@/lib/kwota";
import { sformatujMiesiacDopelniacz } from "@/lib/kwota";
import { NAPISY_PANELU } from "@/lib/napisy";
import { NAPIS_TYPU, TYPY, type DaneBudzetu, type PozycjaPlanu, type TypWpisu } from "@/lib/kontrakt";
import {
  dodajPozycjePlanu,
  zakonczPozycjePlanu,
  zmienPozycjePlanu,
  type OdpowiedzBudzetu,
} from "@/lib/dane/budzet";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import s from "./style.module.css";

/** Tryb panelu. `zmiana` niesie CALA pozycje, bo panel pokazuje jej wartosci. */
export type TrybPanelu =
  | { rodzaj: "dodanie" }
  | { rodzaj: "zmiana"; pozycja: PozycjaPlanu };

// JEDEN NOSNIK ZAMIANY WYJATKU NA ZDANIE DLA CZLOWIEKA — jak w Ksiegowaniu
// i w kontrolce stanu konta. Zdanie silnika oddajemy w CALOSCI, bo to on wie,
// czego mu brakuje („Kategoria 'X' nie istnieje w typie 'Wydatki'…").
// Wyjatek nieznanego rodzaju NIE dostaje wymyslonego brzmienia (§3.7).
function opisBledu(blad: unknown): string {
  if (blad instanceof BladWarstwySieciowej) return `${blad.czegoBrakuje} ${blad.coZrobic}`;
  return NAPISY_PANELU.awariaNieznana;
}

export function PanelPlanu({
  tryb,
  DANE,
  dzis,
  poZapisie,
  zamknij,
}: {
  tryb: TrybPanelu;
  DANE: DaneBudzetu;
  dzis: string | null;
  poZapisie: (dane: DaneBudzetu) => void;
  zamknij: () => void;
}) {
  const idKwoty = useId();
  const idKategorii = useId();
  const idOpisu = useId();
  const idDnia = useId();
  const idCyklu = useId();

  const zmiana = tryb.rodzaj === "zmiana" ? tryb.pozycja : null;

  const [typ, setTyp] = useState<TypWpisu>(zmiana?.typ ?? "Wydatki");
  const [kategoria, setKategoria] = useState(zmiana?.kategoria ?? "");
  const [opis, setOpis] = useState(zmiana?.opis ?? "");
  const [kwotaTekst, setKwotaTekst] = useState(zmiana?.kwota ?? "");
  const [dzienTekst, setDzienTekst] = useState(
    zmiana?.dzien === null || zmiana?.dzien === undefined ? "" : String(zmiana.dzien),
  );
  const [cyklTekst, setCyklTekst] = useState(String(zmiana?.coIleMiesiecy ?? 1));

  const [bladKwoty, setBladKwoty] = useState<string | null>(null);
  const [bladKategorii, setBladKategorii] = useState<string | null>(null);
  const [bladDnia, setBladDnia] = useState<string | null>(null);
  const [bladWarstwy, setBladWarstwy] = useState<string | null>(null);

  // Potwierdzenie konca reguly jest OSOBNYM stanem, nie oknem przegladarki:
  // `confirm()` pisze po angielsku, nie da sie w nim nazwac zakresu skutku
  // i nie zostawia sladu na ekranie.
  const [pytamOKoniec, setPytamOKoniec] = useState(false);

  // ZAMEK NA `useRef`, NIE NA STANIE — powtorka naprawy z Z7c i W8. Stan
  // dociera do funkcji obslugi dopiero przy NASTEPNYM rysowaniu, wiec trzy
  // klikniecia w jednym zadaniu przegladarki czytaja trzy razy `false`.
  // Zamek broni przed WYSCIGIEM ODPOWIEDZI: druga odpowiedz potrafi wrocic
  // pierwsza i ekran pokazalby wtedy plan sprzed poprawki.
  const zamek = useRef(false);
  const [wLocie, setWLocie] = useState(false);

  const miesiacSlownie = sformatujMiesiacDopelniacz(DANE.miesiac);

  function wyczyscBledy() {
    setBladKwoty(null);
    setBladKategorii(null);
    setBladDnia(null);
    setBladWarstwy(null);
  }

  /** Dzien miesiaca i cykl to LICZNIKI, nie kwoty — tu nie ma groszy do
   *  zgubienia i tylko tu w tym pliku wolno wywolac `Number`.
   *  Nazwa zmiennej mowi to w tej samej linii, w ktorej `Number` pada:
   *  straznik `test_ekran_budzet.py::test_kwota_NIE_STAJE_SIE_liczba_
   *  nigdzie_na_ekranie` czyta linie, nie kontekst, i ma prawo. */
  function licznikCzytelny(tekstLicznika: string, od: number, doGory: number): boolean {
    if (!/^\d{1,2}$/.test(tekstLicznika.trim())) return false;
    const licznik = Number(tekstLicznika.trim());
    return licznik >= od && licznik <= doGory;
  }

  async function wykonaj(zadanie: () => Promise<OdpowiedzBudzetu>) {
    if (zamek.current) return;
    zamek.current = true;
    setWLocie(true);
    try {
      const odpowiedz = await zadanie();
      poZapisie(odpowiedz.dane);
      zamknij();
    } catch (blad: unknown) {
      // Awaria do stanu uzytecznego, nie do zera (§3.7): panel ZOSTAJE
      // otwarty z tym, co czlowiek wpisal, i mowi, czego brakuje i co zrobic.
      // Zamkniety po bledzie kazalby wpisywac wszystko drugi raz.
      setBladWarstwy(opisBledu(blad));
    } finally {
      zamek.current = false;
      setWLocie(false);
    }
  }

  async function zapisz() {
    wyczyscBledy();

    const odczyt = odczytajKwote(kwotaTekst);
    let wolno = true;

    if (odczyt.stan === "pusta") {
      setBladKwoty(NAPISY_PANELU.kwotaPusta);
      wolno = false;
    }
    if (odczyt.stan === "nieczytelna") {
      setBladKwoty(NAPISY_PANELU.kwotaNieczytelna);
      wolno = false;
    }
    // MINUS JEST TU BLEDEM, inaczej niz w stanie konta. Kierunek pozycji
    // niesie jej TYP, wiec ujemna kwota planu znaczylaby to samo dwa razy
    // i drugi raz odwrotnie.
    if (odczyt.stan === "ujemna") {
      setBladKwoty(NAPISY_PANELU.kwotaUjemna);
      wolno = false;
    }
    if (zmiana === null && kategoria.trim() === "") {
      setBladKategorii(NAPISY_PANELU.kategoriaPusta);
      wolno = false;
    }
    if (dzienTekst.trim() !== "" && !licznikCzytelny(dzienTekst, 1, 31)) {
      setBladDnia(NAPISY_PANELU.dzienPozaMiesiacem);
      wolno = false;
    }
    if (!licznikCzytelny(cyklTekst, 1, 12)) {
      setBladDnia(NAPISY_PANELU.cyklPozaZakresem);
      wolno = false;
    }
    if (!wolno || odczyt.stan !== "ok") return;

    const dzienPozycji =
      dzienTekst.trim() === "" ? null : Number(dzienTekst.trim());
    const cyklPozycji = Number(cyklTekst.trim());

    if (zmiana !== null) {
      await wykonaj(() =>
        zmienPozycjePlanu(
          zmiana.id,
          { kwota: odczyt.kwota, dzien: dzienPozycji, coIleMiesiecy: cyklPozycji },
          { miesiac: DANE.miesiac, dzis },
        ),
      );
      return;
    }

    await wykonaj(() =>
      dodajPozycjePlanu(
        {
          typ,
          kategoria: kategoria.trim(),
          kwota: odczyt.kwota,
          opis: opis.trim(),
          dzien: dzienPozycji,
          coIleMiesiecy: cyklPozycji,
        },
        { miesiac: DANE.miesiac, dzis },
      ),
    );
  }

  async function zakoncz() {
    if (zmiana === null) return;
    wyczyscBledy();
    await wykonaj(() =>
      zakonczPozycjePlanu(zmiana.id, { miesiac: DANE.miesiac, dzis }),
    );
  }

  function naKlawiszu(zdarzenie: React.KeyboardEvent) {
    if (zdarzenie.key === "Enter") void zapisz();
    if (zdarzenie.key === "Escape") zamknij();
  }

  return (
    <div className={s.panel} role="group" aria-label={zmiana ? NAPISY_PANELU.tytulZmiany : NAPISY_PANELU.tytulDodania}>
      <span className={s.etykietaSekcji}>
        {zmiana ? NAPISY_PANELU.tytulZmiany : NAPISY_PANELU.tytulDodania}
      </span>

      <div className={s.wierszPol}>
        {/* TYP — trzy pozycje wolane z `TYPY` w kontrakcie, nie wpisane tutaj.
            Czwarty typ pojawilby sie tam, a nie w ukladzie ekranu. */}
        {zmiana === null && (
          <div className={s.kolumnaPola}>
            <span className={s.etykietaKolumny}>{NAPISY_PANELU.etykietaTypu}</span>
            <div className={s.przelacznikTypu} role="radiogroup" aria-label={NAPISY_PANELU.etykietaTypu}>
              {TYPY.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={t === typ}
                  className={t === typ ? `${s.kafelekTypu} ${s.kafelekWybrany}` : s.kafelekTypu}
                  onClick={() => setTyp(t)}
                >
                  {NAPIS_TYPU[t]}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className={`${s.kolumnaPola} ${s.kolumnaKategorii}`}>
          <label className={s.etykietaKolumny} htmlFor={idKategorii}>
            {NAPISY_PANELU.etykietaKategorii}
          </label>
          {zmiana === null ? (
            <span className={bladKategorii ? `${s.ramkaPola} ${s.uwaga}` : s.ramkaPola}>
              <input
                id={idKategorii}
                className={s.wpisTekstu}
                autoFocus
                value={kategoria}
                onChange={(e) => setKategoria(e.target.value)}
                onKeyDown={naKlawiszu}
              />
            </span>
          ) : (
            <span className={s.ramkaPola}>
              <span className={s.wpisTekstu} id={idKategorii}>
                {NAPIS_TYPU[zmiana.typ]} · {zmiana.kategoria}
                {zmiana.opis ? ` · ${zmiana.opis}` : ""}
              </span>
            </span>
          )}
          {bladKategorii && (
            <span className={s.podpisUwagi} role="alert">
              {bladKategorii}
            </span>
          )}
        </div>

        <div className={`${s.kolumnaPola} ${s.kolumnaKwoty}`}>
          <label className={s.etykietaKolumny} htmlFor={idKwoty}>
            {NAPISY_PANELU.etykietaKwoty}
          </label>
          <span className={bladKwoty ? `${s.ramkaPola} ${s.uwaga}` : s.ramkaPola}>
            <input
              id={idKwoty}
              className={s.wpisKwoty}
              inputMode="decimal"
              autoFocus={zmiana !== null}
              value={kwotaTekst}
              onChange={(e) => setKwotaTekst(e.target.value)}
              onKeyDown={naKlawiszu}
              aria-describedby={`${idKwoty}-podpis`}
            />
            <span className={s.jednostka}>zł</span>
          </span>
          <span className={s.podpis} id={`${idKwoty}-podpis`}>
            {NAPISY_PANELU.bezZnaku}
          </span>
          {bladKwoty && (
            <span className={s.podpisUwagi} role="alert">
              {bladKwoty}
            </span>
          )}
        </div>

        {zmiana === null && (
          <div className={`${s.kolumnaPola} ${s.kolumnaOpisu}`}>
            <label className={s.etykietaKolumny} htmlFor={idOpisu}>
              {NAPISY_PANELU.etykietaOpisu}
            </label>
            <span className={s.ramkaPola}>
              <input
                id={idOpisu}
                className={s.wpisTekstu}
                value={opis}
                onChange={(e) => setOpis(e.target.value)}
                onKeyDown={naKlawiszu}
              />
            </span>
          </div>
        )}

        <div className={`${s.kolumnaPola} ${s.kolumnaLiczby}`}>
          <label className={s.etykietaKolumny} htmlFor={idDnia}>
            {NAPISY_PANELU.etykietaDnia}
          </label>
          <span className={bladDnia ? `${s.ramkaPola} ${s.uwaga}` : s.ramkaPola}>
            <input
              id={idDnia}
              className={s.wpisTekstu}
              inputMode="numeric"
              value={dzienTekst}
              onChange={(e) => setDzienTekst(e.target.value)}
              onKeyDown={naKlawiszu}
            />
          </span>
          <span className={s.podpis}>{NAPISY_PANELU.dzienPusty}</span>
        </div>

        <div className={`${s.kolumnaPola} ${s.kolumnaLiczby}`}>
          <label className={s.etykietaKolumny} htmlFor={idCyklu}>
            {NAPISY_PANELU.etykietaCyklu}
          </label>
          <span className={s.ramkaPola}>
            <input
              id={idCyklu}
              className={s.wpisTekstu}
              inputMode="numeric"
              value={cyklTekst}
              onChange={(e) => setCyklTekst(e.target.value)}
              onKeyDown={naKlawiszu}
            />
          </span>
        </div>

        <div className={s.kolumnaZapisu}>
          <button
            type="button"
            className={s.wezwaniePanelu}
            onClick={() => void zapisz()}
            disabled={wLocie}
            aria-busy={wLocie}
          >
            {zmiana ? NAPISY_PANELU.zapiszZmiane : NAPISY_PANELU.zapiszNowa}
          </button>
          <button type="button" className={s.rezygnuje} onClick={zamknij}>
            {NAPISY_PANELU.rezygnuje}
          </button>
        </div>
      </div>

      {bladDnia && (
        <span className={s.podpisUwagi} role="alert">
          {bladDnia}
        </span>
      )}

      {zmiana !== null && (
        <div className={s.koniecReguly}>
          <p className={s.tozsamosc}>{NAPISY_PANELU.tozsamoscNieruchoma}</p>
          {pytamOKoniec ? (
            <>
              <p className={s.zdaniePotwierdzenia}>
                {NAPISY_PANELU.potwierdzenieZakonczenia(zmiana.kategoria, miesiacSlownie)}
              </p>
              <div className={s.wierszPotwierdzenia}>
                <button
                  type="button"
                  className={s.wezwaniePanelu}
                  onClick={() => void zakoncz()}
                  disabled={wLocie}
                  aria-busy={wLocie}
                >
                  {NAPISY_PANELU.zakoncz}
                </button>
                <button
                  type="button"
                  className={s.rezygnuje}
                  onClick={() => setPytamOKoniec(false)}
                >
                  {NAPISY_PANELU.rezygnuje}
                </button>
              </div>
            </>
          ) : (
            <button
              type="button"
              className={s.linkCichy}
              onClick={() => setPytamOKoniec(true)}
            >
              {NAPISY_PANELU.zakonczOd(miesiacSlownie)}
            </button>
          )}
        </div>
      )}

      {bladWarstwy && (
        <span className={s.podpisUwagi} role="alert">
          {bladWarstwy}
        </span>
      )}
    </div>
  );
}
