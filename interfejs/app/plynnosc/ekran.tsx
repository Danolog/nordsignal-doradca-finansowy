"use client";

// EKRAN PLYNNOSC — pierwszy, ktory Darek otwiera. Odpowiada na pytanie
// „czy dam rade do konca okresu".
//
// DLACZEGO ROZDZIAL NA DWA PLIKI (W8), tak samo jak w Ksiegowaniu. Dane
// wejsciowe sa z natury serwerowe: przychodza z `GET /api/plynnosc` i maja
// stac w PIERWSZYM rysowaniu, a nie doczytywac sie po nim — inaczej pierwsze
// spojrzenie pada na pustke, ktorej §3.7 zabrania wprost. Uklad od W8 jest
// z natury kliencki: `PUT /api/kotwica` oddaje CALY nowy ekran, wiec po
// zapisie stanu konta zmieniaja sie naraz werdykt, dzien pod kreska, saldo
// minimalne i cala seria — a to znaczy, ze `DANE` musza byc STANEM.
// Wejscie serwerowe zostalo w `page.tsx`; ten plik to `page.tsx` sprzed W8,
// przeniesiony `git mv`, wiec historia pokazuje zmiane nazwy, nie nowy plik.
//
// DRUGIEGO ODPYTANIA PO ZAPISIE NIE MA I TO JEST DECYZJA. `router.refresh()`
// wygladalby prosciej, ale kazalby silnikowi policzyc prognoze DRUGI RAZ dla
// jednej chwili — a odpowiedz `PUT` juz ja niesie. Nosnik tej decyzji stoi po
// drugiej stronie granicy: `api/trasy_plynnosc.py`, akapit „DLACZEGO ZAPIS
// KOTWICY ODDAJE CALY EKRAN".
//
// KRYTERIUM ODBIORU JEST JEDNO: jesli w pierwszej sekundzie nie widac,
// czy jest dobrze czy zle, ekran zawiodl — niezaleznie od poprawnosci
// liczb nizej. Stad JEDNA wielka liczba (56 px wobec 20 px zdania,
// czyli 2,80x przy progu hierarchii 1,5x) i jedna wyrozniona kontrolka.
//
// CZEGO TU NIE MA I NIE WOLNO DOLOZYC: kafelkow przychody/wydatki/
// oszczednosci, celow, majatku, ikony przy werdykcie (werdykt niosa juz
// slowo, barwa i pozycja — ikona bylaby trzecim nosnikiem tej samej rzeczy)
// oraz zdania „Prognoza ich NIE dolicza", ktore MOWI NIEPRAWDE: prognoza
// te raty odejmuje, tyle ze druga droga, jako pozycje planu.
//
// ZERO KWOT W TYM PLIKU. Kazda liczba przychodzi z `lib/dane/plynnosc.ts`
// i jest formatowana przez `lib/kwota.ts`; wspolrzedne rysunku liczy
// `lib/wykres.ts`. Pilnuje tego straznik `testy/test_ekran_plynnosc.py`.
//
// GDZIE TEN EKRAN STOI (W7). Do W7 lezal pod `app/page.tsx`, czyli pod
// adresem `/` — a pasek renderuje `href={`/${klucz}`}` i prowadzil na
// `/plynnosc`, gdzie nie bylo niczego. Zmierzone przed zmiana: wszystkie
// dziewiec odsylaczy paska = HTTP 404, w tym odsylacz do TEGO ekranu.
// Ekran przeniesiony pod swoj wlasny klucz; `app/page.tsx` zostalo
// przekierowaniem. Wybor drogi jest jawny: pole `adres` w mapie ekranow
// byloby DRUGIM NOSNIKIEM faktu, ktory `klucz` juz niesie — dokladnie tym,
// co `makiety/ekrany.py` odrzucilo raz przy polu `aktywna_w_pasku`.
//
// PODPIECIE (Z7): `lib/dane/plynnosc.ts` przestal byc stala i stal sie
// wywolaniem `GET /api/plynnosc`. Uklad nizej NIE ZMIENIL SIE — zmienil sie
// wylacznie sposob, w jaki `DANE` powstaja: z argumentu, a nie z importu.
// To byla teza podejscia „frontend najpierw" i tutaj jest sprawdzana.

import { useState } from "react";
import { Powloka } from "../powloka";
import { Kotwica } from "./kotwica";
import { NAPISY_KOTWICY, NAPISY_PLYNNOSCI } from "@/lib/napisy";
import {
  sformatujDzien,
  sformatujDzienSlownie,
  sformatujKwote,
  sformatujOdczyt,
  znakKwoty,
} from "@/lib/kwota";
import type { DanePlynnosci } from "@/lib/kontrakt";
import { ulozKarte } from "@/lib/karta-dzialania";
import { NAPISY_KARTY } from "@/lib/napisy";
import {
  SZEROKOSC,
  WYSOKOSC,
  liniaZera,
  odcinekPodKreska,
  pierwszyPunktPodKreska,
  punkty,
  sciezka,
} from "@/lib/wykres";
import s from "./style.module.css";

function Strzalka() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8h9M8.5 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Prognoza rysowana KRESKA PRZERYWANA. Linia ciagla twierdzilaby wiedze;
// to jest przewidywanie. Roznica niesie sie bez barwy, a jezyk zostaje
// zarezerwowany: gdy narosnie historia, przeszlosc bedzie ciagla.
function Wykres({ DANE }: { DANE: DanePlynnosci }) {
  const pkt = punkty(DANE.wykres);
  const zero = liniaZera(DANE.wykres);
  const pod = odcinekPodKreska(pkt);
  const znacznik = pierwszyPunktPodKreska(pkt);
  const opis =
    `Prognoza od ${sformatujDzienSlownie(DANE.wykres[0].dzien)} do ` +
    `${sformatujDzienSlownie(DANE.koniecOknaCoMnieCzeka)}; kreską przerywaną, bo to ` +
    (DANE.dzienPodKreska
      ? `przewidywanie; od ${sformatujDzienSlownie(DANE.dzienPodKreska)} biegnie pod kreską zera.`
      : "przewidywanie; nie schodzi pod kreskę zera.");

  return (
    <svg width={SZEROKOSC} height={WYSOKOSC} viewBox={`0 0 ${SZEROKOSC} ${WYSOKOSC}`} role="img" aria-label={opis}>
      {/* Linia zera jest ODCIETA od liniatury rubryki: ta niesie znaczenie,
          tamta jest dekoracja. Gdyby wygladaly tak samo, oko wrzucilo by
          niosaca do klasy ozdobnych — a klasyfikuje z wygladu, zanim
          przeczyta. */}
      {zero !== null && (
        <line x1="0" y1={zero.toFixed(1)} x2={SZEROKOSC} y2={zero.toFixed(1)} stroke="var(--atrament-cichy)" strokeWidth="1" />
      )}
      <path d={sciezka(pkt)} fill="none" stroke="var(--atrament)" strokeWidth="1.6" strokeDasharray="6 4" />
      {pod && (
        <path d={pod} fill="none" stroke="var(--saldo-ujemne)" strokeWidth="3" strokeDasharray="6 4" />
      )}
      {znacznik && (
        <circle cx={znacznik.x.toFixed(1)} cy={znacznik.y.toFixed(1)} r="4.5" fill="var(--saldo-ujemne)" />
      )}
    </svg>
  );
}

// KARTA „CO MAM ZROBIC" — trzecie pytanie aplikacji, osadzone na ekranie
// pierwszym miedzy werdyktem a przyciskiem „Co mnie czeka" (D-54).
//
// Karta STOI ZAWSZE, takze w miesiacu bez deficytu i w stanie startowym.
// Znikajaca uczylaby, ze jej pojawienie sie oznacza klopot — a to buduje
// odruch nieotwierania aplikacji wtedy, gdy jest najbardziej potrzebna.
//
// Karta NIE POWTARZA werdyktu: nazywa DZIALANIE, nie fakt. Fakt stoi wyzej
// przy 56 px; najwiekszy stopien wewnatrz karty to 15 px, czyli 3,73x mniej —
// pierwszenstwo wiersza zamkniecia zostaje nienaruszone.
function KartaDzialania({ DANE }: { DANE: DanePlynnosci }) {
  const karta = ulozKarte(DANE);
  return (
    <div className={s.karta}>
      <span className={s.etykietaSekcji}>{NAPISY_KARTY.tytul}</span>
      {karta.stan === "brak-danych" ? (
        <p className={s.zdanieKarty}>{karta.zdanie}</p>
      ) : (
        <div className={s.trescKarty}>
          <p className={s.zdanieKarty}>{karta.zdanie}</p>
          <p className={s.kosztKarty}>{karta.koszt}</p>
        </div>
      )}
    </div>
  );
}

// UKLAD. `poczatkowe` przychodzi z komponentu serwerowego obok; od pierwszego
// zapisu stanu konta zrodlem jest odpowiedz `PUT /api/kotwica`.
//
// `dzis` przekazywany z adresu jest UMYSLNY i ma nosnik po drugiej stronie:
// `api/wspolne.py::dzien` mowi wprost, ze parametr istnieje DLA POMIARU
// ODBIORCZEGO — bramka wymaga ustalonego dnia, zeby jej wynik nie zalezal od
// godziny przebiegu. Bez parametru silnik bierze dzien dzisiejszy.
export function Ekran({
  poczatkowe,
  dzis,
}: {
  poczatkowe: DanePlynnosci;
  dzis: string | null;
}) {
  const [DANE, setDane] = useState<DanePlynnosci>(poczatkowe);
  return <Uklad DANE={DANE} dzis={dzis} poZapisie={setDane} />;
}

function Uklad({
  DANE,
  dzis,
  poZapisie,
}: {
  DANE: DanePlynnosci;
  dzis: string | null;
  poZapisie: (dane: DanePlynnosci) => void;
}) {
  // OTWARCIE KONTROLKI STANU KONTA STOI TUTAJ, NIE W NIEJ SAMEJ — bo ma DWA
  // wejscia stojace w dwoch miejscach ukladu: wezwanie „Podaj stan konta"
  // (stan startowy, ramka `NieWiem.dc.html`) i DOPISEK przy wierszu otwarcia
  // (stan z odczytem, ramka `Main.dc.html`). Stan trzymany wewnatrz kontrolki
  // bylby niewidoczny dla drugiego z nich.
  const [kotwicaOtwarta, setKotwicaOtwarta] = useState(false);

  const ksiega = DANE.ksiega;
  const tenSamDzien = (a: number, b: number) =>
    a >= 0 && b < ksiega.length && ksiega[a]?.dzien === ksiega[b]?.dzien;

  // `null` = stan startowy: nie ma kotwicy, wiec nie ma czego zamykac.
  // Wiersz zamkniecia znika, a karta „Co mam zrobic" mowi, czego brakuje.
  const zamkniecie =
    DANE.saldoMinimalne !== null && DANE.dataSaldaMinimalnego !== null
      ? { kwota: DANE.saldoMinimalne, dzien: DANE.dataSaldaMinimalnego }
      : null;

  return (
    <Powloka
      aktywny="plynnosc"
      odczyt={sformatujOdczyt(DANE.odczyt)}
      straznik={DANE.ostatnieSprawdzenie}
      pion="srodek"
      odstepStopki={28}
    >
      <section className={s.ekran}>

        <div className={s.ksiega}>
          <div className={s.tytulBloku}>
            <span className={s.etykietaSekcji}>{NAPISY_PLYNNOSCI.tytul}</span>
            <span className={s.podpis}>{DANE.okresNapis}</span>
          </div>

          {/* Pusta seria = prognozy NIE MA (brak kotwicy). Rysunek z zerowa
              liczba punktow bylby prostokatem bez linii, a podpisy osi
              opisywalyby dni, ktorych nikt nie policzyl — czyli etykieta
              opisywalaby liczbe, ktorej nie ma (CLAUDE.md §3.5). Czego
              brakuje, mowia wtedy zdanie werdyktu i karta „Co mam zrobic",
              i to sa jedyne dwa miejsca, ktore maja o tym mowic (§3.7). */}
          {DANE.wykres.length > 0 && (
            <div className={s.kafelWykresu}>
              <Wykres DANE={DANE} />
              <div className={s.osDat}>
                <span className={s.podpisOsi}>
                  {NAPISY_PLYNNOSCI.osDzis(sformatujDzien(DANE.wykres[0].dzien))}
                </span>
                <span className={s.rozpychacz} />
                {DANE.dzienPodKreska && (
                  <>
                    <span className={s.podpisOsiPodKreska}>
                      {NAPISY_PLYNNOSCI.osPodKreska(sformatujDzien(DANE.dzienPodKreska))}
                    </span>
                    <span className={s.rozpychacz} />
                  </>
                )}
                <span className={s.podpisOsi}>
                  {sformatujDzien(DANE.koniecOknaCoMnieCzeka)}
                </span>
              </div>
            </div>
          )}

          <div className={s.wierszKolumn}>
            <span className={s.naglowekKolumny}>{NAPISY_PLYNNOSCI.kolumnaDzien}</span>
            <span className={s.naglowekKolumny}>{NAPISY_PLYNNOSCI.kolumnaPozycja}</span>
            <span className={`${s.naglowekKolumny} ${s.doPrawej}`}>{NAPISY_PLYNNOSCI.kolumnaKwota}</span>
            <span className={`${s.naglowekKolumny} ${s.doPrawej}`}>{NAPISY_PLYNNOSCI.kolumnaSaldo}</span>
          </div>

          {ksiega.map((w, i) => {
            // Data pisze sie raz na dzien, a kreska rozdziela DNI, nie wiersze.
            const kontynuacja = tenSamDzien(i - 1, i);
            const przedDalszym = tenSamDzien(i, i + 1);
            const klasa = [
              s.wiersz,
              przedDalszym ? s.wierszPrzedDalszym : "",
              kontynuacja ? s.wierszDalszyZDnia : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <div key={`${w.dzien}-${w.pozycja}`} className={klasa}>
                <span className={s.komorkaDnia}>{kontynuacja ? "" : sformatujDzien(w.dzien)}</span>
                <span className={s.komorkaPozycji}>
                  {w.pozycja}
                  {/* Odstep stoi PRZED znacznikiem, nie w srodku: wewnatrz mial by
                      13 px zamiast 15 px i dopisek przesuwal by sie o piksel w lewo. */}
                  {/* DOPISEK KOTWICY JEST KONTROLKA (W8) — jedyne wejscie do
                      zmiany stanu konta, gdy odczyt juz jest. Stoi PRZY
                      LICZBIE, ktora zmienia (§3.5), i nie kosztuje ani
                      jednego piksela: wyglada dokladnie jak napis, ktorym
                      byl. Osobny przycisk zepchnalby ekran o 80 px w dol —
                      zmierzone, odwzorowanie 14,38% przy progu 2%. */}
                  {w.dopisek &&
                    (w.kwota === null ? (
                      <>
                        {" "}
                        <button
                          type="button"
                          className={s.dopiseKotwicy}
                          onClick={() => setKotwicaOtwarta(true)}
                          title={NAPISY_KOTWICY.zmienOdczyt}
                          aria-label={`${w.dopisek} — ${NAPISY_KOTWICY.zmienOdczyt}`}
                        >
                          {w.dopisek}
                        </button>
                      </>
                    ) : (
                      <>{" "}<span className={s.dopisek}>{w.dopisek}</span></>
                    ))}
                </span>
                {w.kwota === null ? (
                  <span className={s.komorkaBezKwoty}>{NAPISY_PLYNNOSCI.brakKwoty}</span>
                ) : (
                  <span className={s.komorkaKwoty}>
                    {sformatujKwote(w.kwota, znakKwoty(w.kwota))}
                  </span>
                )}
                {/* Stan na dzis dostaje 28 px, reszta kolumny 15 px.
                    Drabina 56 / 28 / 20 / 15: test pieciu sekund przechodzil
                    dla „co mnie czeka", a nie przechodzil dla „ile mam
                    pieniedzy" — kotwica stala w tej samej wadze, co cztery
                    salda posrednie. Wiersz zamkniecia zostaje jedyna
                    czerwienia i jedynym stopniem 56 px: 56/28 = 2,00x
                    przy progu 1,5x. */}
                <span
                  className={
                    w.kwota === null ? `${s.komorkaSalda} ${s.komorkaSaldaKotwicy}` : s.komorkaSalda
                  }
                >
                  {w.saldoPoDniu === null ? "" : sformatujKwote(w.saldoPoDniu, "neutralna")}
                </span>
              </div>
            );
          })}

          {zamkniecie && (
            <>
              <div className={s.wierszZamkniecia}>
                <span />
                <span className={s.etykietaZamkniecia}>
                  {NAPISY_PLYNNOSCI.najnizej(sformatujDzienSlownie(zamkniecie.dzien))}
                </span>
                <span />
                <span
                  className={`${s.liczbaZamkniecia} ${
                    znakKwoty(zamkniecie.kwota) === "ujemna"
                      ? s.zamknieciePonizejZera
                      : s.zamknieciePowyzejZera
                  }`}
                >
                  {sformatujKwote(zamkniecie.kwota, znakKwoty(zamkniecie.kwota))}
                </span>
              </div>
              <div className={s.kreska} />
              <div className={s.przerwa} />
              <div className={s.kreska} />
            </>
          )}
        </div>

        <div className={s.werdykt}>
          <p className={s.zdanieWerdyktu}>{DANE.zdanieWerdyktu}</p>
          <p className={s.horyzont}>{NAPISY_PLYNNOSCI.horyzont(DANE.horyzontDni)}</p>
        </div>

        <Kotwica
          DANE={DANE}
          dzis={dzis}
          otwarta={kotwicaOtwarta}
          ustawOtwarta={setKotwicaOtwarta}
          poZapisie={poZapisie}
        />

        <KartaDzialania DANE={DANE} />

        <div className={s.wierszWezwania}>
          <span className={s.rozpychacz} />
          <a className={`${s.wezwanie} ${s.przycisk}`} href="/co-mnie-czeka">
            <span>
              {NAPISY_PLYNNOSCI.coMnieCzeka(
                DANE.liczbaPozycjiCoMnieCzeka,
                sformatujDzienSlownie(DANE.koniecOknaCoMnieCzeka)
              )}
            </span>
            <Strzalka />
          </a>
        </div>

      </section>
    </Powloka>
  );
}
