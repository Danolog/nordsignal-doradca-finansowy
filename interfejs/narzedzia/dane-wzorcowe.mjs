// WZORCOWY ZESTAW DANYCH — WŁASNOŚĆ RAMKI, NIE APLIKACJI (D-63).
//
// PO CO ISTNIEJE. Bramka odwzorowania (`porownaj-z-makieta.mjs`) dowodzi
// JEDNEJ rzeczy: że ekran wygląda jak rysunek. To jest twierdzenie o układzie
// i typografii. Puszczona na żywych danych mierzy naraz układ I miesiąc —
// i nie umie ich rozdzielić, więc przestaje być dowodem czegokolwiek.
// Zmierzone 2026-08-29: `Main` na planie Darka daje 14,45% przy progu 2%,
// bo ramka rysuje miesiąc Z DEFICYTEM (6 pozycji, −210,67 zł), a plan Darka
// daje 7 pozycji i +7 485,98 zł. Układ był przez cały czas dobry.
//
// DLACZEGO NIE PRZERYSOWUJEMY RAMKI (rozstrzygnięcie Sophii, D-63).
// Przerysowanie `Main.dc.html` pod plan Darka zniszczyłoby STAN DEFICYTOWY —
// a to jest stan, dla którego zaprojektowano cały pierwszy ekran: wiersz
// zamknięcia w czerwieni, zdanie werdyktu, karta „Co mam zrobić" w stanie 1.
// Oddalibyśmy rysunek złego stanu za zgodność z danymi JEDNEGO miesiąca,
// a dane zmieniają się co miesiąc. Stan nadwyżkowy ma własną ramkę:
// `Main-Dobrze.dc.html`.
//
// DLACZEGO TE LICZBY MIESZKAJĄ TUTAJ, A NIE W `lib/dane/`.
// Ten sam powód, dla którego mieszka tu stan `ksiegowanie-z-ramki`: wartości
// są własnością RAMKI, nie aplikacji. Po Z7 w `lib/dane/` nie ma ani jednej
// kwoty i pilnuje tego strażnik `testy/test_dane_bez_kwot.py`; wzorzec
// wpuszczony tam znosiłby tamtą regułę tylnymi drzwiami.
//
// SKĄD SIĘ BIORĄ. Z rubryk ramek, znak po znaku — nie z pamięci. Pięć sald
// `Main` jest odczytanych wprost i jest dokładne co do grosza:
// 9 601,03 · 8 295,98 · 8 145,98 · 3 025,33 · −210,67. Trzy dalsze punkty
// serii (30 IX, 1 X, 13 X) NIE STOJĄ w rubryce — ramka niesie je wyłącznie
// jako współrzędne rysunku, z dokładnością 0,1 px. Odtworzone przez
// odwrócenie skali wykresu; **błąd odczytu ±11 zł** (0,05 px na 44 px
// wysokości przy rozpiętości 9 811,70 zł). To jest granica pomiaru, nie
// zaokrąglenie — i dlatego stoi napisana, zamiast udawać, że te trzy liczby
// są tej samej klasy co pozostałe pięć.
//
// STRAŻNIK PRZED DRYFEM: `testy/wzorzec.test.ts` wycina liczby z ramek przy
// każdym przebiegu i porównuje je z tym plikiem. Wzorzec, który rozjedzie
// się z ramką, jest gorszy niż brak wzorca — bramka meldowałaby wtedy
// zgodność z rysunkiem, którego nikt już nie rysuje.

/** Spacja nierozdzielająca — dokładnie ta, którą niosą ramki (`&nbsp;`). */
const NB = " ";

/** Seria dzienna o stałym saldzie — `ile` kolejnych dni od `od`. */
function serie(od, ile, saldo) {
  const [rok, miesiac, dzien] = od.split("-").map(Number);
  return Array.from({ length: ile }, (_, i) => {
    const d = new Date(Date.UTC(rok, miesiac - 1, dzien + i));
    return { dzien: d.toISOString().slice(0, 10), saldo };
  });
}

/* ---------- Main.dc.html — miesiąc z deficytem ---------- */

const MAIN = {
  odczyt: "2026-10-06",
  okresNapis: "wrzesień 2026 · 45 dni naprzód",
  ksiega: [
    {
      dzien: "2026-09-02",
      pozycja: "Stan na dziś",
      dopisek: `— z odczytu 9${NB}920,79${NB}zł z 1 września`,
      kwota: null,
      saldoPoDniu: "9601.03",
    },
    { dzien: "2026-09-12", pozycja: "Kredyt Revolut",    dopisek: null, kwota: "-1305.05", saldoPoDniu: "8295.98" },
    { dzien: "2026-09-15", pozycja: "PGNiG",             dopisek: null, kwota: "-150.00",  saldoPoDniu: "8145.98" },
    { dzien: "2026-09-21", pozycja: "ZUS",               dopisek: null, kwota: "-5120.65", saldoPoDniu: "3025.33" },
    // Oba wiersze 25 IX mają `saldoPoDniu: null`. Saldo tego dnia jest
    // najniższym punktem prognozy i stoi niżej jako wiersz zamknięcia;
    // powtórzone w rubryce byłoby tą samą liczbą dwa razy, a druga
    // wyglądałaby na błąd rachunku.
    { dzien: "2026-09-25", pozycja: "Czesne WSB Merito", dopisek: null, kwota: "-660.00",  saldoPoDniu: null },
    { dzien: "2026-09-25", pozycja: "VAT",               dopisek: null, kwota: "-2576.00", saldoPoDniu: null },
  ],
  wykres: [
    ...serie("2026-09-02", 10, "9601.03"),   // 2–11 IX
    ...serie("2026-09-12", 3, "8295.98"),    // 12–14 IX
    ...serie("2026-09-15", 6, "8145.98"),    // 15–20 IX
    ...serie("2026-09-21", 4, "3025.33"),    // 21–24 IX
    ...serie("2026-09-25", 5, "-210.67"),    // 25–29 IX — pod kreską
    ...serie("2026-09-30", 1, "8196.26"),    // 30 IX  — odczyt z rysunku, ±11 zł
    ...serie("2026-10-01", 11, "7861.84"),   // 1–11 X — odczyt z rysunku, ±11 zł
    ...serie("2026-10-12", 6, "6568.68"),    // 12–17 X — odczyt z rysunku, ±11 zł
  ],
  dzienPodKreska: "2026-09-25",
  saldoMinimalne: "-210.67",
  dataSaldaMinimalnego: "2026-09-25",
  zdanieWerdyktu:
    `25${NB}września schodzisz poniżej zera — tego dnia wychodzi VAT i czesne.`,
  horyzontDni: 23,
  liczbaPozycjiCoMnieCzeka: 7,
  koniecOknaCoMnieCzeka: "2026-10-17",
  ostatnieSprawdzenie: "Ostatnie sprawdzenie: dziś 06:00 — nic pilnego nie znalazł.",
};

/* ---------- Main-Dobrze.dc.html — miesiąc z nadwyżką ---------- */
//
// TA RAMKA NIE RYSUJE WYKRESU — i to nie jest przeoczenie rysownika.
// `wykres: []` znaczy dla ekranu „prognozy nie ma czym narysować" i kafel
// wykresu w ogóle nie wchodzi do drzewa. Pusta seria jest tu więc DANĄ,
// nie brakiem danych.
//
// `saldoMinimalne` niesie WIODĄCY PLUS. Ramka rysuje „+2 468,39 zł", a znak
// czyta `znakKwoty()` z zapisu kwoty — bez plusa ekran narysowałby
// „2 468,39 zł" i wyróżnienie dodatniej wartości zniknęłoby. To jest
// jednocześnie ZGŁOSZENIE: żywy silnik oddaje dodatnie `saldoMinimalne`
// bez znaku (zmierzone: „11090.44"), więc na miesiącu z nadwyżką wiersz
// „Najniżej" nie dostaje plusa, którego żąda ramka.
const MAIN_DOBRZE = {
  odczyt: "2026-10-06",
  okresNapis: "sierpień 2026 · 45 dni naprzód",
  ksiega: [
    {
      dzien: "2026-08-28",
      pozycja: "Stan na dziś",
      dopisek: `— z odczytu 1${NB}840,55${NB}zł z 27 sierpnia`,
      kwota: null,
      saldoPoDniu: "1840.55",
    },
    { dzien: "2026-08-31", pozycja: "Przychód JDG",      dopisek: null, kwota: "8400.00",  saldoPoDniu: "10240.55" },
    { dzien: "2026-09-01", pozycja: "Kredyt Alior",      dopisek: null, kwota: "-319.76",  saldoPoDniu: "9920.79" },
    { dzien: "2026-09-12", pozycja: "Kredyt Revolut",    dopisek: null, kwota: "-1305.05", saldoPoDniu: "8615.74" },
    { dzien: "2026-09-15", pozycja: "PGNiG",             dopisek: null, kwota: "-150.00",  saldoPoDniu: "8465.74" },
    { dzien: "2026-09-21", pozycja: "ZUS",               dopisek: null, kwota: "-2761.35", saldoPoDniu: "5704.39" },
    { dzien: "2026-09-25", pozycja: "Czesne WSB Merito", dopisek: null, kwota: "-660.00",  saldoPoDniu: null },
    { dzien: "2026-09-25", pozycja: "VAT",               dopisek: null, kwota: "-2576.00", saldoPoDniu: null },
  ],
  wykres: [],
  dzienPodKreska: null,
  saldoMinimalne: "+2468.39",
  dataSaldaMinimalnego: "2026-09-25",
  zdanieWerdyktu: "Przez 6 miesięcy nie schodzisz poniżej zera.",
  horyzontDni: 23,
  liczbaPozycjiCoMnieCzeka: 8,
  koniecOknaCoMnieCzeka: "2026-10-12",
  ostatnieSprawdzenie: "Ostatnie sprawdzenie: dziś 06:00 — nic pilnego nie znalazł.",
};

/* ---------- Ksiegowanie.dc.html ---------- */

const kategoria = (nazwa) => ({ nazwa, aktywna: true, systemowa: false });

// DŁUG JAWNY PO D-62 (2026-08-29, SHA `db2b60a`): TEN WZORZEC NIESIE CZTERY
// WIERSZE KARTY, A PRODUKCJA RYSUJE PIĘĆ.
// Piąty wiersz — `Płynność` — dołożył Max po stronie silnika. Wzorzec go NIE
// dostaje i to jest decyzja, nie przeoczenie: wzorzec ma być tym, co rysuje
// ramka, a `makiety/Ksiegowanie.dc.html` rysuje cztery wiersze. Wpisany tutaj
// piąty czyniłby bramkę odwzorowania zieloną wobec rysunku, którego nie ma.
//
// CENA, NAZWANA: bramka odwzorowania jest wobec piątego wiersza **ŚLEPA** —
// zmierzone 2026-08-29, `Ksiegowanie` daje 0,12% i przed, i po D-62, bo na
// wzorcu ekran rysuje cztery wiersze. Rozjazd ramki z produktem kosztuje
// (zmierzone w przeglądarce na żywym silniku) **+52 px wysokości strony**
// w brzmieniach dwuwierszowych i **+70 px** w brzmieniu „w planie",
// czyli 1 024 i 1 042 px wobec 972 px ramki.
//
// STRAŻNIK I PRÓG: `testy/wzorzec.test.mjs`, test „liczba wierszy karty
// w ramce zgadza się z wzorcem" liczy wiersze siatki w ramce między nagłówkami
// „Co ruszy ten wpis" i „Czego tu nie ma". Czerwieni się w chwili, w której
// Mila dorysuje piąty wiersz — i wtedy, i tylko wtedy, wzorzec go dostaje.
const KSIEGOWANIE = {
  dzisiaj: "2026-10-06",
  typDomyslny: "Wydatki",
  // Trzy pierwsze to pozycje planu na październik; dalej alfabetycznie.
  kategorie: [
    "Czesne", "Energia Elektryczna", "Kredyty", "Gaz", "Inne",
    "Jedzenie poza domem", "Monika i Ada", "PUWIS", "Podatki i ZUS",
    "Praca", "Subskrypcje", "Telefon i Internet", "Transport", "Zakupy",
    "Zdrowie",
  ].map(kategoria),
  uzasadnienieKolejnosci:
    "Kolejność ma się liczyć z częstości wpisów, a tych po 1 IX 2026 jeszcze nie ma — " +
    "więc na początku stoją trzy kategorie z planu na październik, dalej alfabetycznie. " +
    "Przeliczy się sama, gdy wpisy będą.",
  ostatnieWpisy: [],
  liczbaWpisowWMiesiacu: 0,
  nazwaMiesiaca: "październiku",
  podglad: {
    kwota: "274.06",
    wiersze: [
      { etykieta: "Wydatki w październiku", przed: "0,00", po: `274,06${NB}zł`, wyjasnienie: null },
      { etykieta: "Energia Elektryczna",    przed: "0,00", po: `274,06${NB}zł`, wyjasnienie: null },
      { etykieta: "Plan wydatków wykonany", przed: "0,0%", po: "10,5%",         wyjasnienie: null },
      {
        etykieta: "Wolne środki",
        przed: "",
        po: null,
        wyjasnienie: "bez zmian — liczą się z planu, nie z wpisów",
      },
    ],
  },
  ostatnieSprawdzenie: "Ostatnie sprawdzenie: dziś 06:00 — nic pilnego nie znalazł.",
};

/* ---------- dwa stany rozróżnienia „nie wiem" / „zero" (D-64) ---------- */
//
// NIE POCHODZĄ Z ŻADNEJ RAMKI i dlatego nie wolno ich mierzyć bramką
// odwzorowania. Istnieją po to, żeby dało się ZOBACZYĆ oba renderowania
// przycisku „Co mnie czeka" na prawdziwym ekranie — `null` znaczy
// „nie policzyłem", `0` znaczy „policzyłem i nie ma". Zero renderowane jako
// „nie wiem" albo `null` renderowane jako zero to ta sama klasa wady co
// forma opodatkowania zgadnięta wartością domyślną.
const NIE_WIEM = {
  ...MAIN,
  liczbaPozycjiCoMnieCzeka: null,
  zdanieWerdyktu:
    "Nie policzę prognozy — brakuje stanu konta, od którego miałaby ruszyć.",
};

const ZERO = {
  ...MAIN,
  liczbaPozycjiCoMnieCzeka: 0,
};

/* ---------- Budzet.dc.html — pazdziernik 2026, plan bez ani jednego wpisu ---------- */
//
// ODCZYTANE Z RUBRYK RAMKI, ZNAK PO ZNAKU. Trzy kafelki (2 614,81 · 7 696,65 ·
// 10 311,46), bilans (−2 614,81), trzy wiersze „Plan kontra wykonanie"
// (1 624,81 · 660,00 · 330,00), jeden cel (30 000,00, tempo „2 000,00 zl / mc
// przez 15 mc") i licznik naglowka („4 pozycje planu · 0 wpisow").
// Kontrola: 2 614,81 + 7 696,65 = 10 311,46 ✓; 30 000 / 15 = 2 000 ✓.
//
// JEDNA LICZBA Z RAMKI JEST W TYM KSZTALCIE NIEWYRAZALNA i stoi to tutaj
// napisane, zamiast udawac, ze sie zgadza. Ramka pisze „Kredyty 1 624,81 zl
// (1 i 12 X)" — czyli SUMUJE dwie reguly planu tej samej kategorii
// (1 305,05 + 319,76) i skleja ich dni. `PozycjaPlanu.dzien` niesie JEDEN
// dzien, wiec „1 i 12 X" nie ma jak powstac; wzorzec niesie jedna pozycje
// Kredytow o kwocie z ramki i dniu `1`. Ekran napisze wiec „(1 X)" tam,
// gdzie ramka pisze „(1 i 12 X)" — roznica NAZWANA, nie zamieciona.
// Zgodne z licznikiem naglowka: ramka liczy Kredyty jako JEDNA pozycje
// (4 = trzy wydatki + jeden cel).
//
// `liczbaPozycjiPlanu` w wierszu „Kredyty" wynosi wiec 1, a nie 2 — bo tak
// widzi to ramka. Gdyby wynosila 2, `idPozycjiPlanu` musialoby byc `null`
// i nazwa kategorii przestalaby otwierac panel zmiany.

const BUDZET = {
  dzisiaj: "2026-10-06",
  miesiac: "2026-10",
  miesiacNapis: "październik 2026",
  nazwaMiesiaca: "październiku",
  liczbaPozycjiPlanu: 4,
  liczbaWpisow: 0,
  kafelki: [
    {
      klucz: "wydatkiZPlanu",
      tytul: "Wydatki osobiste z planu",
      kwota: "2614.81",
      dopisek: "przepływ tego miesiąca",
      wyjasnienie: null,
    },
    {
      klucz: "rezerwa",
      tytul: "Rezerwa na podatki",
      kwota: "7696.65",
      dopisek: "saldo narastające, nie wydatek miesiąca",
      wyjasnienie: null,
    },
    {
      klucz: "razem",
      tytul: "Plan miesiąca razem",
      kwota: "10311.46",
      dopisek: "to jest kwota z ekranu Miesiąc",
      wyjasnienie: null,
    },
  ],
  planPrzychodow: "0.00",
  planWydatkow: "2614.81",
  planOszczednosci: "0.00",
  bilansPlanu: "-2614.81",
  wykonaneWydatki: "0.00",
  // Kolejnosc z ramki i zarazem NAJWIEKSZE ODCHYLENIE U GORY:
  // −1 624,81 · −660,00 · −330,00.
  pozycjeWykonania: [
    {
      typ: "Wydatki", kategoria: "Kredyty",
      plan: "1624.81", wykonane: "0.00", odchylenie: "-1624.81",
      procent: "0,0%", procentPaska: 0, przekroczone: false,
      idPozycjiPlanu: 1, liczbaPozycjiPlanu: 1,
    },
    {
      typ: "Wydatki", kategoria: "Czesne",
      plan: "660.00", wykonane: "0.00", odchylenie: "-660.00",
      procent: "0,0%", procentPaska: 0, przekroczone: false,
      idPozycjiPlanu: 2, liczbaPozycjiPlanu: 1,
    },
    {
      typ: "Wydatki", kategoria: "Energia Elektryczna",
      plan: "330.00", wykonane: "0.00", odchylenie: "-330.00",
      procent: "0,0%", procentPaska: 0, przekroczone: false,
      idPozycjiPlanu: 3, liczbaPozycjiPlanu: 1,
    },
  ],
  // Kolejnosc z silnika: (typ, kategoria, opis). Zdanie narracyjne wymienia
  // pozycje w tej samej kolejnosci, w ktorej je dostaje — sortowanie po dniu
  // byloby DRUGIM nosnikiem porzadku, obok tego, ktory ustala silnik.
  pozycjePlanu: [
    { id: 2, typ: "Wydatki", kategoria: "Czesne", opis: "",
      kwota: "660.00", dzien: 25, coIleMiesiecy: 1, czeka: true },
    { id: 3, typ: "Wydatki", kategoria: "Energia Elektryczna", opis: "",
      kwota: "330.00", dzien: 20, coIleMiesiecy: 1, czeka: true },
    { id: 1, typ: "Wydatki", kategoria: "Kredyty", opis: "",
      kwota: "1624.81", dzien: 1, coIleMiesiecy: 1, czeka: true },
  ],
  cele: [
    {
      id: 1, nazwa: "Poduszka finansowa", kategoria: "Poduszka finansowa",
      kwotaDocelowa: "30000.00", uzbierane: "0.00", brakuje: "30000.00",
      procent: "0,0%", procentPaska: 0, termin: "2028-01-31",
      tempoNapis: `2${NB}000,00${NB}zł / mc przez 15 mc`,
      osiagniety: false, poTerminie: false,
    },
  ],
  historia: [],
  miesiacKopiujZ: "2026-09",
  napisKopiujZ: "Skopiuj z września",
  ostatnieSprawdzenie: "Ostatnie sprawdzenie: dziś 06:00 — nic pilnego nie znalazł.",
};

/** Wszystkie zestawy — JEDEN nośnik odpowiedzi „jakie wzorce znamy". */
export const ZESTAWY = {
  main: { plynnosc: MAIN, ksiegowanie: KSIEGOWANIE, budzet: BUDZET },
  "main-dobrze": { plynnosc: MAIN_DOBRZE, ksiegowanie: KSIEGOWANIE, budzet: BUDZET },
  ksiegowanie: { plynnosc: MAIN, ksiegowanie: KSIEGOWANIE, budzet: BUDZET },
  budzet: { plynnosc: MAIN, ksiegowanie: KSIEGOWANIE, budzet: BUDZET },
  "nie-wiem": { plynnosc: NIE_WIEM, ksiegowanie: KSIEGOWANIE, budzet: BUDZET },
  zero: { plynnosc: ZERO, ksiegowanie: KSIEGOWANIE, budzet: BUDZET },
};

// ZNACZNIK OBECNOŚCI WZORCA — zdanie, które stoi na ekranie WYŁĄCZNIE wtedy,
// gdy ekran dostał dane stąd, a nie z żywego silnika. Bramka odwzorowania
// sprawdza je przed pomiarem: bez tego przebieg wobec przypadkiem
// uruchomionego prawdziwego silnika zmierzyłby pogodę i zameldował wynik.
// Żywy silnik oddaje tu `null` (nie ma jeszcze przebiegów strażnika),
// więc powłoka rysuje wtedy zdanie o niepodpiętym strażniku.
export const ZNACZNIK_WZORCA = "Ostatnie sprawdzenie: dziś 06:00 — nic pilnego nie znalazł.";
