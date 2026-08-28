// EKRAN PLYNNOSCI — pierwszy ekran, jedyny, ktory Darek dzis otwiera.
//
// STAN: szkielet. Ramka wiazaca: `makiety/Main.dc.html` (900 px wysokosci).
// Do zbudowania wg PRD §10.2: ksiega dzien-pozycja-kwota-saldo, wykres
// z trzema punktami odniesienia, saldo minimalne z podpisem "NAJNIZEJ",
// zdanie wyjasniajace przyczyne, wejscie "Co mnie czeka — N pozycji",
// oraz karta "Co mam zrobic" (PRD §11.2 — TEJ NIE MA NA RAMCE, wymaga
// projektu przed budowa).
//
// CZEGO TU CELOWO NIE MA: danych przykladowych. D-33 — stan pusty zamiast
// danych przykladowych; na ekranie, gdzie kolejnosc jest trescia, przykladowy
// ranking to przykladowa odpowiedz, a etykieta go nie ratuje.

export default function Plynnosc() {
  return (
    <section>
      <h1>Płynność</h1>
      <p>
        Szkielet. Silnik nie jest jeszcze podpięty, więc ten ekran nie pokazuje
        żadnej kwoty — <strong>i to jest zamierzone</strong>. Liczba bez
        policzonego źródła wygląda tak samo jak liczba prawdziwa.
      </p>
      <p>
        Wiążąca specyfikacja tego ekranu: <code>makiety/Main.dc.html</code>.
        Bramka odbioru: porównanie maszynowe zrzutu z ramką przy tej samej
        szerokości (PRD §12.7).
      </p>
    </section>
  );
}
