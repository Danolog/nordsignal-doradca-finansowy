// DANE EKRANU KSIEGOWANIE — otypowane kontraktem, w kolejnosci z ramki.
//
// SKAD SIE TU BIORA LICZBY. To jest STAN POKAZOWY Z RAMKI, nie odczyt z bazy.
// Ramka `makiety/Ksiegowanie.dc.html` jest wiazaca specyfikacja wygladu
// (CLAUDE.md §3.6), a bramka odwzorowania porownuje z nia zrzut ekranu —
// wiec ekran musi umiec pokazac dokladnie ten stan. Kwoty stoja TUTAJ,
// a nie w komponencie, i pilnuje tego straznik
// `test_ekran_NIE_MA_wpisanej_recznie_kwoty`.
//
// PROG WYMIANY, JAWNY: przy podpieciu tras (Z6/Z7) ten plik znika, a jego
// miejsce zajmuje odpowiedz `GET /api/ksiegowanie`. Wtedy pole kwoty
// startuje PUSTE, a `podglad` liczy sie z kwoty wpisanej przez uzytkownika.
//
// HORYZONT (D-23): 204 wpisy z 2025 to historia. Wrzesien 2026 zaczyna sie
// od zera, dlatego `ostatnieWpisy` jest puste, a `przed` w podgladzie wynosi
// 0,00 — to nie jest zaslepka, to zmierzony stan pierwszego miesiaca.
//
// BEZ KATEGORII KOSZTU FIRMOWEGO (D-24): koszt firmowy ma jedno miejsce —
// ekran Firma, razem z VAT-em i numerem dokumentu. Straznik
// Straznik zakresu szuka tu nazwy tej kategorii doslownie, wiec nie pada
// ona nawet w komentarzu.

import type { DaneKsiegowania, Kategoria } from "../kontrakt";

const kategoria = (nazwa: string): Kategoria => ({
  nazwa,
  aktywna: true,
  systemowa: false,
});

// Trzy pierwsze to pozycje planu na pazdziernik; dalej alfabetycznie.
// Kolejnosc jest JEDNA regula (czestosc wpisow, remisy alfabetycznie) —
// przelicza ja silnik, nie ten plik.
export const KATEGORIE_WYDATKOW: readonly Kategoria[] = [
  kategoria("Czesne"),
  kategoria("Energia Elektryczna"),
  kategoria("Kredyty"),
  kategoria("Gaz"),
  kategoria("Inne"),
  kategoria("Jedzenie poza domem"),
  kategoria("Monika i Ada"),
  kategoria("PUWIS"),
  kategoria("Podatki i ZUS"),
  kategoria("Praca"),
  kategoria("Subskrypcje"),
  kategoria("Telefon i Internet"),
  kategoria("Transport"),
  kategoria("Zakupy"),
  kategoria("Zdrowie"),
];

export const PODPIS_PASMA = "15 kategorii wydatków · na razie od pozycji planu";

export const DANE: DaneKsiegowania = {
  dzisiaj: "2026-10-06",
  typDomyslny: "Wydatki",
  kategorie: KATEGORIE_WYDATKOW,
  uzasadnienieKolejnosci:
    "Kolejność ma się liczyć z częstości wpisów, a tych po 1 IX 2026 jeszcze nie ma — " +
    "więc na początku stoją trzy kategorie z planu na październik, dalej alfabetycznie. " +
    "Przeliczy się sama, gdy wpisy będą.",
  ostatnieWpisy: [],
  liczbaWpisowWMiesiacu: 0,
  nazwaMiesiaca: "październiku",
  podglad: {
    kwota: "274.06",
    // Czwarty wiersz jest wazniejszy od trzech pierwszych, bo mowi, co sie
    // NIE ruszylo. `po: null` znaczy „bez zmian" i wtedy `wyjasnienie` podaje
    // powod — inaczej Darek szukalby ruchu, ktorego nie ma, i uznalby to
    // za wade obliczen.
    wiersze: [
      { etykieta: "Wydatki w październiku", przed: "0,00", po: "274,06 zł" },
      { etykieta: "Energia Elektryczna", przed: "0,00", po: "274,06 zł" },
      { etykieta: "Plan wydatków wykonany", przed: "0,0%", po: "10,5%" },
      {
        etykieta: "Wolne środki",
        przed: "",
        po: null,
        wyjasnienie: "bez zmian — liczą się z planu, nie z wpisów",
      },
    ],
  },
};

// Stan pokazowy formularza — dokladnie ten, ktory niesie ramka.
export const STAN_POKAZOWY = {
  kwota: "274.06",
  szczegoly: "prąd, rozliczenie za wrzesień",
  kategoria: "Energia Elektryczna",
};
