# Baza robocza — gdzie leży i czym jest

**Wersja:** v1.0 · 2026-08-29 · autor: Ethan (CTO)

## Decyzja, z której to wynika

Darek, 2026-08-29 godz. 09:19: *„na razie pozostaw starą bazę dla budowy aplikacji"*.
Dwie rzeczy, które łatwo zlepić w jedną, są rozdzielone:

- **Z czym aplikacja wystartuje 1 września** → **pusto.** Zero migracji: 204 wpisy i 46 pozycji
  planu z poprzedniej aplikacji **nie wchodzą** do bazy tego projektu.
- **Na czym budujemy ją dziś** → **kopia bazy poprzednika.** Bramki odbiorcze nocy 2026-08-29
  są liczone na tych danych i bez nich nie dają się odtworzyć.

## Gdzie leży

```
/Users/dariuszgradzik/Dane-robocze-doradca-finansowy/
├── CO-TO-JEST.md                    ← opis przy plikach, prawa 600
├── robocza-2026-08-29-z7.db         ← 204 wpisy, 46 pozycji planu, 24 kategorie
└── robocza-2026-08-29-z7c.db        ← ten sam stan + wiersz `przebiegi_straznika`
```

**Poza repozytorium — sprawdzone komendą, nie założone:**

```
cd /Users/dariuszgradzik/Dane-robocze-doradca-finansowy && git rev-parse --show-toplevel
fatal: not a git repository (or any of the parent directories): .git
```

## Dlaczego nie w repozytorium i dlaczego nie w katalogu tymczasowym

**Nie w repozytorium**, bo to są **prawdziwe finanse Darka**. `.gitignore` wymienia
`cfo_database.db` z nazwy i łapie `*.db` wzorcem; strażnik
`testy/test_magazyn.py::test_baza_jest_w_gitignore` pyta o nazwę, nie o wzorzec.

**Nie w katalogu tymczasowym**, bo do 2026-08-29 obie kopie stały w `/private/tmp/…/scratchpad/`
— czyli w miejscu kasowanym przy sprzątaniu systemu. Jedyna podstawa wszystkich bramek
odbiorczych nocy stała w katalogu, który znika bez ostrzeżenia.

## Czym NIE jest

Nie jest bazą produkcyjną nowej aplikacji i nigdy nią nie będzie. Historia 2025 żyje **wyłącznie**
w `../AI CFO` — ten katalog pozostaje nietknięty.

## Jak jej użyć

```
AI_CFO_BAZA="/Users/dariuszgradzik/Dane-robocze-doradca-finansowy/robocza-2026-08-29-z7.db" \
  ./.venv/bin/python -m uvicorn api.index:aplikacja
```

**Nigdy pod pytestem.** `testy/conftest.py` zakłada strażnika ścieżki: pod pytestem rozwiązanie
się na bazę produkcyjną (tego projektu albo poprzednika) jest błędem, nie ostrzeżeniem. Każdy
test stoi na własnym pliku w katalogu tymczasowym.

## Co przez skasowanie tych plików przestanie działać

Pozycja obowiązkowa (`CLAUDE.md` §3.11). Odpowiedź **nie brzmi „niczym"**.

Przestaną być odtwarzalne wszystkie bramki odbiorcze nocy 2026-08-29 liczone na żywym silniku:
`saldoMinimalne 11 090,44 zł`, trzy przypadki podziału osi (`55,94 zł` reszty pozycji,
`−170,00 zł` nadwyżki, `−500,00 zł` przy kategorii bez planu) oraz pomiar piątego wiersza karty
w przeglądarce. **Nie przestanie działać** bramka odwzorowania makiety — ta stoi na wzorcu
z `interfejs/narzedzia/dane-wzorcowe.mjs`, który nie dotyka bazy.

Odtworzenie wymagałoby ponownej kopii z `../AI CFO/cfo_database.db`, o ile tamta baza wtedy
jeszcze istnieje.

## Co się z nią stało przy schemacie 12

Otwarcie kopii nowym kodem podnosi wersję schematu z 11 na 12 i **przed** migracją robi kopię
pliku obok. Liczności zmierzone po migracji (na kopii w katalogu tymczasowym, nie na plikach
wyżej):

```
wpisy_budzetu      204
plan_budzetu        46
kategorie           24
rejestr_stawek      19
user_version        12
```

Zero utraty wierszy. Trzy nowe kolumny weszły ścieżką `_DOPISYWANE_KOLUMNY`; rozjazdy nazwane
tamże, z progiem.
