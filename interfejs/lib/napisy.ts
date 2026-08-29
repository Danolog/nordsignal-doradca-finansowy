// JEDEN NOSNIK BRZMIEN EKRANU KSIEGOWANIE.
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
