# Pierwsze uruchomienie — co musisz podać, żeby aplikacja zaczęła liczyć

**Wersja:** v1.0 · 2026-08-29 · autor: Ethan (CTO) · **status: do przeczytania przez Darka**

Aplikacja startuje **pusta** 1 września 2026 (Twoja decyzja z 2026-08-29, godz. 08:44).
Żaden z 204 wpisów z 2025 roku ani 46 pozycji planu nie wchodzi do jej bazy — zostają
w starej aplikacji jako historia.

Pusta baza znaczy: **aplikacja nie policzy nic, dopóki jej nie powiesz, od czego ma zacząć.**
Ten dokument mówi, czego dokładnie potrzebuje, w jakiej kolejności — i, co ważniejsze,
**czego dziś nie da się jej powiedzieć, bo nie ma gdzie**.

---

## Osiem rzeczy, w kolejności

Kolejność nie jest dowolna. Każda następna pozycja korzysta z poprzedniej.

| # | Co podajesz | Po co | Gdzie to wpiszesz DZIŚ |
|---|---|---|---|
| 1 | **Ile masz na koncie i z którego dnia ten odczyt** | punkt startu prognozy | **NIE MA POLA** — jest tylko połączenie po stronie serwera |
| 2 | **Plan miesiąca**: raty, czesne, prąd, gaz — kwota i dzień | prognoza wie, co Cię obciąży | **NIE MA NICZEGO** |
| 3 | **Ile godzin zamierzasz przepracować i po ile za godzinę** | prognoza wie, co wpłynie | **NIE MA NICZEGO** |
| 4 | **Data rozpoczęcia działalności** (1 IX 2026) | liczba miesięcy, za które należy się ZUS | **NIE MA NICZEGO** |
| 5 | **Kredyty**: nazwa, kapitał, rata | wykaz zobowiązań | **NIE MA NICZEGO** |
| 6 | **Majątek**: konta, oszczędności | obraz stanu posiadania | **NIE MA NICZEGO** |
| 7 | **Zatwierdzenie 19 stawek** podatkowych i składkowych | żeby aplikacja liczyła liczbami, które podpisałeś | **NIE MA NICZEGO** |
| 8 | **Bieżące wydatki i przychody** | wykonanie planu, wpływ na płynność | **JEST** — ekran „Księgowanie" |

---

## Werdykt: siedem pozycji z ośmiu nie ma dziś gdzie zostać wpisanych

To jest najważniejsza rzecz w tym dokumencie i została zmierzona, nie oszacowana.

**Sprawdzone na pustej bazie 2026-08-29.** Aplikacja zachowuje się poprawnie — mówi, czego jej
brakuje, zamiast pokazywać zera:

```
GET /api/plynnosc  →  saldoMinimalne: null
   "Nie policzę prognozy: nie wiem, ile masz na koncie. Saldo z budżetu to suma wpisów,
    a nie pieniądze — prognoza zbudowana na nim startowałaby z punktu, który nie istnieje.
    Wpisz stan konta i datę odczytu."
```

Problem jest po drugiej stronie: **nie ma gdzie tego wpisać.**

**Pozycja 1 (stan konta) — trasa jest, pola nie ma.** Serwer przyjmuje odczyt salda i po jego
podaniu prognoza natychmiast rusza (sprawdzone: po podaniu 5 000,00 zł z 1 września ekran mówi
*„Nie schodzisz poniżej zera — najniżej masz 5 000,00 zł 1 września"*). Ale funkcja zapisu
w interfejsie **nie ma ani jednego wołającego**, a ekran Płynność **nie ma ani jednego pola
do wpisania**:

```
grep -rn "zapiszKotwice" interfejs/ --include=*.ts --include=*.tsx   →  1 trafienie
   interfejs/lib/dane/plynnosc.ts:32:export function zapiszKotwice(     ← sama definicja
grep -rn "<input|<form" interfejs/app/page.tsx                       →  0 trafień
```

**Pozycje 2–7 — nie ma ani połączenia z serwerem, ani ekranu.** Sprawdzone wprost:

```
POST /api/plan             → 404        PUT  /api/forma          → 404
POST /api/zobowiazania     → 404        PUT  /api/dzialalnosc    → 404
POST /api/majatek          → 404        POST /api/stawki/zatwierdz → 404
```

Zbudowane są **dwa ekrany z jedenastu** zaplanowanych: Płynność i Księgowanie. Brakuje między
innymi ekranów „Budżet" (pozycja 2), „Godziny" (3), „Ustawienia" (4 i 7), „Majątek" (5 i 6).

---

## Co aplikacja robi w międzyczasie — i dlaczego trzeba o tym wiedzieć

**Pokazuje przychód, którego nie zadeklarowałeś.** Na pustej bazie prognoza wpisuje
**8 400,00 zł przychodu na 30 września**. Ta liczba to `120 godzin × 70 zł` — wartości startowe
wpisane w kodzie na czas, zanim podasz własne (pozycja 3 listy). Nie jest zmyślona i nie jest
błędem, ale **nie jest też Twoja**. Dopóki nie podasz swoich godzin i stawki, prognoza opisuje
kogoś innego.

**Formę opodatkowania na 2026 wpisuje sama: SKALA.** To wynika z ustalenia, że przed
zawieszeniem działalności byłeś na zasadach ogólnych, a milczenie do 20 października utrwala
skalę. **Rok 2027 zostaje pusty** i zachowuje się jak „nie wiem" — i nie ma dziś gdzie go wskazać.

**Słownik 24 kategorii wsiewa się sam.** Nie musisz go wpisywać.

**19 stawek podatkowych i składkowych leży w bazie jako propozycje.** Żadna nie jest
zatwierdzona — i to jest zamierzone: status „zatwierdzona" ma znaczyć „Darek to potwierdził",
a nie „ktoś to przepisał". **Uwaga: dziś zatwierdzenie i tak niczego nie zmieni** — silnik liczy
z liczb wpisanych w kodzie, a nie z tej tabeli. Tabela ma dane i nie ma odbiorcy.

---

## Czego potrzebuję od Ciebie — jedna rzecz

**Decyzji, czym zajmujemy się najpierw: pozycją 1 czy pozycją 2.**

- **Pozycja 1 (pole na stan konta)** jest tańsza — połączenie z serwerem już działa, brakuje
  samego pola na ekranie. Po niej aplikacja zaczyna liczyć cokolwiek.
- **Pozycja 2 (plan miesiąca)** jest droższa — potrzebny cały ekran i cztery nowe połączenia.
  Ale bez niej prognoza pokazuje pustą przyszłość: nie wie o żadnej racie, czesnym ani rachunku,
  więc wygląda znacznie lepiej, niż jest.

**Bez tej decyzji** zespół sam wybierze kolejność, a Ty zobaczysz wynik dopiero na końcu.
**Co się bez tego nie wydarzy:** nic się nie zatrzyma — ale ryzykujemy, że 1 września dostaniesz
aplikację, której nie da się uruchomić od zera, mimo że na starych danych działa bez zarzutu.
