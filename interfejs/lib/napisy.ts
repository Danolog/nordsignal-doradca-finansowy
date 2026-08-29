// JEDEN NOSNIK BRZMIEN INTERFEJSU.
//
// `NAPISY` — ekran Ksiegowanie. `NAPISY_PLYNNOSCI` — ekran Plynnosc.
// `NAPISY_POWLOKI` — naglowek i stopka wspolne wszystkim ekranom.
// Komponent WOLA te napisy, nigdy ich nie wpisuje. Powod nie jest porzadkowy:
// komunikat wpisany w widok rozjezdza sie z komunikatem silnika po cichu,
// a uzytkownik dostaje wtedy dwa rozne zdania o jednej regule.
//
// SIEDEM STANOW BLEDU (§41.5 specyfikacji) stoi tu w komplecie — takze
// przypadek (g), niemozliwy z konstrukcji. Brzmienie stanu niemozliwego
// zapisujemy JAWNIE, zamiast go pomijac: gdy stan sie kiedys wydarzy,
// uzytkownik ma zobaczyc zdanie, a nie pusty ekran (CLAUDE.md §3.7).
//
// DLUG NOSNIKA, NAZWANY (Z-19a ze specyfikacji §41.5): podpis `bezZnaku`
// i pytanie `kwotaUjemna` niosa te sama regule dwoma zdaniami. Skrotu NIE
// wyprowadzam ze zdania dlugiego, bo skladanie napisu z kawalkow zabiera
// straznikowi zakresu mozliwosc znalezienia frazy w zrodle. Zamiast tego:
//   STRAZNIK: `testy/test_ekran_ksiegowanie.py`,
//             `test_podpis_bez_znaku_i_pytanie_o_minus_mowia_to_samo`.
//   PROG:     przy pierwszej zmianie ktoregokolwiek z tych dwoch zdan —
//             wtedy oba wyprowadzamy z `silnik/prezentacja.py` (Z4/Z5).

import { DOPELNIACZ_TYPU, type TypWpisu } from "./kontrakt";

export const NAPISY = {
  // --- etykiety ekranu, w kolejnosci ramki ---
  tytul: "Księgowanie",
  etykietaDatyWpisu: "Data wpisu",
  etykietaKwoty: "Kwota",
  etykietaSzczegolow: "Szczegóły — nieobowiązkowe",
  etykietaKategorii: "Kategoria",
  bezZnaku: "Bez znaku — minus jest w typie wpisu.",
  zapisz: "Zapisz wpis",
  coZostajePoZapisie:
    "Po zapisie zostają data, typ i kategoria — czyści się kwota i szczegóły. " +
    "Trzy takie same zakupy pod rząd to trzy kwoty i trzy razy ",
  coZostajePoZapisieAkcent: "Zapisz",
  coZostajePoZapisieOgon: ".",

  // Podpis pasma kategorii. Mowi WYLACZNIE to, co da sie policzyc z tego,
  // co pasmo pokazuje: ile kafelkow stoi i jakiego sa typu.
  //
  // DO Z7 STALO TU DRUGIE ZDANIE — „· na razie od pozycji planu" — i po
  // podpieciu bylby to DRUGI NOSNIK reguly kolejnosci. Pierwszym i jedynym
  // jest `ekran_ksiegowanie.uzasadnienie_kolejnosci`, ktore przychodzi
  // z silnika jako `uzasadnienieKolejnosci` i stoi pod pasmem. Tamto zdanie
  // zmienia brzmienie po pierwszym wpisie; to nie zmienialoby sie nigdy
  // i klamalo by od drugiego dnia (CLAUDE.md §3.5).
  podpisPasma: (ile: number, typ: TypWpisu) =>
    `${ile} ${ile === 1 ? "kategoria" : "kategorii"} ${DOPELNIACZ_TYPU[typ]}`,

  tytulPodgladu: "Co ruszy ten wpis",
  podpisPodgladu: (kwota: string) => `po zapisaniu ${kwota}`,

  tytulCzegoTuNieMa: "Czego tu nie ma",
  tytulOstatnichWpisow: "Ostatnie wpisy",
  licznikWpisow: (ile: number, miesiac: string) => `${ile} w ${miesiac}`,
  pustaHistoria: "Jeszcze ani jednego wpisu.",

  // --- siedem stanow bledu (§41.5) ---
  blad: {
    // (a) data nieczytelna — pod kontrolka daty
    dataNieczytelna: "Nieczytelna data.",
    // (b) kwota pusta — pod polem kwoty
    kwotaPusta: "Podaj kwotę.",
    // (c) kwota nieczytelna — pod polem kwoty
    kwotaNieczytelna: "Nieczytelna kwota.",
    // (d) kwota ujemna — NIE blad, tylko PYTANIE z przyciskiem potwierdzenia.
    //     Uzytkownik nie zrobil literowki: powiedzial prawde w zlym jezyku.
    //     Ekran NIE zapisuje po cichu — zamiana znaku bez pytania byla by
    //     interfejsem, ktory poprawia liczby uzytkownika bez jego wiedzy.
    kwotaUjemna: (kwota: string, typ: string) =>
      `Minus jest już w typie wpisu. Zapisać ${kwota} jako ${typ}?`,
    kwotaUjemnaPotwierdzenie: "Tak, zapisz",
    // (e) kategoria niewybrana — pod pasmem, pasmo dostaje obrys uwagi
    kategoriaNiewybrana: "Wybierz kategorię.",
    // (f) kategoria nieaktywna — pod pasmem
    kategoriaNieaktywna: (nazwa: string) =>
      `Kategoria »${nazwa}« jest nieaktywna — nie przyjmuję do niej nowych wpisów. ` +
      "Przywróć ją w Ustawieniach.",
    // (g) typ nieznany — niemozliwy z konstrukcji (przelacznik ma trzy pozycje
    //     wolane z `TYPY` w kontrakcie). Brzmienie stoi tu mimo to.
    typNieznany:
      "Nieznany typ wpisu. Przełącznik ma trzy pozycje, więc ten stan nie " +
      "powinien powstać — zgłoś to, zanim wpiszesz cokolwiek dalej.",
    // OSMY STAN, spoza §41.5: awaria warstwy sieciowej o nieznanym rodzaju.
    // Silnik ma dla swoich odmow wlasne zdania i te oddajemy w calosci
    // (`BladWarstwySieciowej`); to brzmienie stoi WYLACZNIE dla wyjatku,
    // ktorego nie umiemy nazwac — i mowi wprost, czyja to wada.
    awariaNieznana:
      "Coś padło po naszej stronie i nie umiem powiedzieć co. Wpis NIE został " +
      "zapisany — zgłoś to, zanim spróbujesz ponownie.",
  },
} as const;

// Proza z ramki, rozbita na czlony: czlon z `akcent: true` to nazwa ekranu,
// pisana atramentem pelnym. Rozbicie stoi TUTAJ, a nie w komponencie, zeby
// zdanie mialo jeden nosnik razem ze swoim wyrozniemiem.
export type Czlon = { tekst: string; akcent?: boolean };

export const PROZA: Readonly<Record<string, readonly Czlon[]>> = {
  czegoTuNieMa: [
    { tekst: "Faktura kosztowa i faktura sprzedaży idą przez ekran " },
    { tekst: "Firma", akcent: true },
    {
      tekst:
        " — niosą VAT i numer dokumentu, których ten formularz nie zbiera. " +
        "Koszt firmowy nie ma tu kategorii — od tej wersji zapisuje się go wyłącznie na ",
    },
    { tekst: "Firmie", akcent: true },
    { tekst: ", razem z VAT-em i numerem dokumentu." },
  ],
  pustaHistoriaPowod: [
    {
      tekst:
        "Działalność ruszyła 1 IX 2026 i od tego dnia nic tu nie trafiło. " +
        "Pierwszy wpis pojawi się w tym miejscu razem z przyciskiem ",
    },
    { tekst: "wycofaj", akcent: true },
    { tekst: ", czynnym przez sześć ostatnich pozycji." },
  ],
  pustaHistoriaHoryzont: [
    {
      tekst:
        "204 wpisy sprzed wznowienia działalności zostają w bazie, ale nie wchodzą " +
        "do żadnego okresu tej aplikacji — ani tutaj, ani na ",
    },
    { tekst: "Raportach", akcent: true },
    { tekst: "." },
  ],
} as const;

/* ---------- POWLOKA ---------- */

export const NAPISY_POWLOKI = {
  // Strażnik, który nigdy nie działał, MÓWI o tym wprost. Zero nigdy nie
  // zastępuje „nie wiem" — zdanie o sprawdzeniu, którego nie było, jest
  // gorsze niż brak zdania (CLAUDE.md §3.7).
  straznikNieDzialal:
    "Ostatnie sprawdzenie: brak danych — strażnik nie jest jeszcze podpięty.",
} as const;

/* ---------- EKRAN AWARII (§3.7) ---------- */

// Brzmienia stale ekranu awarii. Zdanie o tym, CZEGO BRAKUJE, i zdanie o tym,
// CO ZROBIC, przychodza z `BladWarstwySieciowej` — bo w przypadku odmowy
// silnika sa to JEGO slowa, oddane w calosci. Tutaj stoi wylacznie rama.
export const NAPISY_AWARII = {
  tytul: "Nie mam skąd wziąć liczb",
  // Naglowek pyta „z ktorego dnia jest to, co widze". Przy awarii odpowiedz
  // brzmi „nie wiem" i ma tak brzmiec — data wpisana na sztywno byla by
  // dokladnie ta liczba z nieznanego zrodla, przed ktora broni ten ekran.
  odczytNieznany: "odczyt nieznany",
} as const;

/* ---------- ADRES BEZ EKRANU (W7, §3.7) ---------- */

// DWA STANY, DWA ZDANIA — i to sa ROZNE stany, nie jeden z dwoma brzmieniami.
//
//   (1) ADRES ZNANY, EKRAN NIEZBUDOWANY — pozycja stoi w mapie ekranow
//       (`lib/ekrany.ts`), ma swoje pytanie i swoja ramke, tylko nie ma
//       jeszcze kodu. Uzytkownik trafil tu z paska i pasek NIE SKLAMAL.
//   (2) ADRES NIEZNANY — w mapie nie ma nic o tej nazwie. Uzytkownik trafil
//       tu z zakladki, z literowki albo z odsylacza, ktorego nie piszemy.
//
// Zlanie ich w jedno zdanie kosztowaloby dokladnie to, po co ten ekran
// istnieje: „nie ma tego" i „jeszcze tego nie zrobilem" prowadza do dwoch
// roznych ruchow uzytkownika.
//
// ZERO LICZB NA OBU EKRANACH. Kwota, licznik albo „0 pozycji" byly by
// liczba z nieznanego zrodla — czyli tym, przed czym broni §3.7.

export const NAPISY_NIEZBUDOWANEGO = {
  tytul: "Tej części jeszcze nie ma",

  // Pytanie ekranu przychodzi z mapy ekranow i jest oddane w calosci —
  // to JEGO zdanie, nie nasze. Skrocone do samej nazwy przestaje mowic,
  // czego uzytkownik sie tu nie dowie.
  //
  // ZDANIE NIE MOWI „stoi w pasku" — i to jest poprawka po pomiarze, nie
  // ostroznosc. Pierwsze brzmienie tak mowilo i na `/co-mnie-czeka` bylo
  // NIEPRAWDA: „Co mnie czeka" jest rozwinieciem otwieranym przyciskiem
  // z ekranu Plynnosci, nie pozycja paska (`makiety/ekrany.py`, ROZWINIECIA).
  // Wykryte odczytem wyrenderowanego ekranu, nie czytaniem kodu.
  zdanie: (napis: string, pytanie: string) =>
    `»${napis}« ma odpowiadać na pytanie: „${pytanie}”. ` +
    "Ekranu jeszcze nie zbudowałem — nic tu nie policzyłem i żadnej liczby nie zmyślam.",

  instrukcja: (start: string) =>
    `Nie ma tu nic do zrobienia. Wróć paskiem u góry — odsyłacz »${start}« ` +
    "prowadzi na ekran startowy.",
} as const;

export const NAPISY_NIEZNANEGO_ADRESU = {
  tytul: "Nie znam tego adresu",

  // „Nie zgaduje" jest tu tym samym zdaniem, co przy adresie silnika
  // w `next.config.mjs`: ekran zgadniety wyglada tak samo jak wlasciwy,
  // wiec zgadywanie zamienia pomylke w cicha nieprawde.
  zdanie:
    "Pod tym adresem nic w tej aplikacji nie stoi. Nie zgaduję, o który ekran chodziło — " +
    "zgadnięty wyglądałby tak samo jak właściwy.",

  instrukcja: (start: string) =>
    `Wybierz obszar z paska u góry; odsyłacz »${start}« prowadzi na ekran startowy.`,
} as const;

/* ---------- EKRAN PLYNNOSCI ---------- */

export const NAPISY_PLYNNOSCI = {
  tytul: "Księga płynności",

  // Nagłówki kolumn rubryki, w kolejności ramki.
  kolumnaDzien: "Dzień",
  kolumnaPozycja: "Pozycja",
  kolumnaKwota: "Kwota",
  kolumnaSaldo: "Saldo po tym dniu",

  // Wiersz otwarcia: kwoty nie ma, więc kolumna mówi „—", a nie „0,00 zł".
  brakKwoty: "—",

  // Podpisy osi wykresu. Skrajne dwa niosą datę, środkowy — dzień zejścia.
  osDzis: (dzien: string) => `${dzien} — dziś`,
  osPodKreska: (dzien: string) => `${dzien} — pod kreską`,

  // ETYKIETA WIELKIEJ LICZBY. Bez niej liczba stoi w wierszu VAT-u i czyta
  // się jako kwota VAT-u — wykryte przy oglądaniu zrzutu, nie przy pisaniu
  // kodu. Skasowanie tej etykiety zmienia znaczenie ekranu, nie jego wygląd.
  najnizej: (dzienSlownie: string) => `Najniżej — ${dzienSlownie}`,

  // Etykieta jest ta sama, gdy prognoza NIE schodzi pod zero: opisuje
  // najnizszy punkt, a nie „problem". Osobne brzmienie na ten przypadek
  // byloby drugim nosnikiem tego samego zdania.

  horyzont: (dni: number) => `Masz ${dni} dni.`,

  // `null` = NIE POLICZYLEM, `0` = policzylem i nic nie czeka (Z7b).
  // Do Z7b kontrakt niosl tu goly `number`, wiec przy odmowie prognozy
  // wychodzilo „Co mnie czeka — 0 pozycji", czyli DOBRA WIADOMOSC podana
  // wtedy, gdy nie ma zadnej wiadomosci. Przyczyne odmowy niesie na tym
  // samym ekranie `zdanieWerdyktu`, wiec ten napis jej NIE POWTARZA —
  // powtorzony powod bylby drugim nosnikiem jednego zdania.
  coMnieCzeka: (pozycji: number | null, doDnia: string) =>
    pozycji === null
      ? "Co mnie czeka — jeszcze nie policzyłem"
      : `Co mnie czeka — ${pozycji} pozycji do ${doDnia}`,
} as const;

/* ---------- KARTA „CO MAM ZROBIC" (D-54, D-56) ---------- */

// Trzecie pytanie aplikacji: „co mam z tym zrobic". Brzmienia przeniesione
// doslownie z ramki `makiety/CoMamZrobic.dc.html`, ktora opisuje TRZY stany
// karty; strazniki w `interfejs/testy/karta.test.ts` porownuja je znak
// po znaku z tekstem wycietym z ramek.
//
// KARTA NIE ZNIKA W DOBRYM MIESIACU. Karta znikajaca uczy, ze jej pojawienie
// sie oznacza klopot — a to buduje odruch nieotwierania aplikacji wtedy,
// gdy jest najbardziej potrzebna.
//
// ZAKRES v1 TO DOKLADNIE JEDNO DZIALANIE (D-56): C1 „ile moge odlozyc".
// Nie ma tu ukladu na dwie ani na trzy pozycje i nie dorabiamy tresci
// do pustych miejsc.
export const NAPISY_KARTY = {
  tytul: "Co mam zrobić",

  // Stan 1 — jest co robic. Kwota jest UJEMNA WERSJA tej samej liczby, ktora
  // jako dodatnia bylaby kwota do odlozenia: karta nie liczy niczego nowego,
  // tylko czyta ten sam wynik inaczej. Zdanie mowi to wprost, zeby nikt nie
  // szukal drugiego rachunku.
  deficytZdanie: (kwota: string, dzien: string) =>
    `Nie odkładaj nic w tym miesiącu — brakuje ${kwota}, żeby ${dzien} zostać na plusie. ` +
    "To ta sama kwota, co „Najniżej” wyżej.",
  deficytKoszt: (dzien: string) =>
    `Koszt: żadnej nowej poduszki do ${dzien} — pierwsza okazja na oszczędności wraca po tym dniu.`,

  // Stan 2 — wszystko w porzadku. Jedna pozycja, bez wymyslonego drugiego
  // dzialania na sile.
  nadwyzkaZdanie: (kwota: string) =>
    `Możesz odłożyć nawet ${kwota} w tym miesiącu — linia ostrożna zostaje dodatnia ` +
    "do końca okna. To ta sama kwota, co „Najniżej” wyżej.",
  nadwyzkaKoszt:
    "Koszt: o tyle mniej luzu w budżecie, gdyby w tym miesiącu wypadł nieplanowany wydatek.",

  // Stan 3 — brak danych. Karta nie znika i NIE ZMYSLA liczby: nazywa, czego
  // brakuje, i wskazuje istniejaca akcje na tym samym ekranie, zamiast
  // dokladac drugi przycisk robiacy to samo.
  brakDanych:
    "Jeszcze nie wiem, ile możesz odłożyć — brakuje stanu konta, od którego liczy się " +
    "prognoza. Podaj go wyżej, żeby zobaczyć tę liczbę.",
} as const;
