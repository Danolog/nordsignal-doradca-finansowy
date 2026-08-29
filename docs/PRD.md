# Doradca Finansowy — dokument wymagań produktu (PRD)

**Wersja:** v1.4 · 2026-08-29 · autor: Ethan (CTO) · bump: Sophia (Product Owner) · **status: do sign-offu Darka**

**Changelog v1.3 → v1.4 — sześć decyzji produktowych z recenzji zadania Z3, jedno sprostowanie
cudzej przesłanki, trzy nowe pozycje niezweryfikowane. Zero zmian zakresu poza kartą „Co mam
zrobić".** Recenzja pracy Mili (commit `2d5587d`) przez Sophię (PO). **D-54** wpuszcza kartę
„Co mam zrobić" do v1; **D-56** zawęża jej zakres do C1. **D-55 blokuje jeden element tamtej
pracy**: linia „Ile mogę jeszcze rozdysponować we wrześniu" wróciła na ekran Płynność na
przesłance *„Sophia już raz zdecydowała, że zostaje"* — przesłanka sprawdzona w nośniku
pierwotnym i **obalona**: decyzja D-10 istniała, ale została **uchylona przez D-16 Darka** tego
samego dnia o 16:50. **D-57** rozstrzyga znak słowny na `FINANSE` i wskazuje **jedną** wartość
wiążącą dla wykonawcy, bo ramki i kod mówiły dziś co innego. **D-58** rozstrzyga znak minus na
korzyść ramki. **D-59** odrzuca brzmienie sekcji „Gdzie leżą dane" — dane o położeniu danych mają
być **odczytem, nie obietnicą**. Pozycje 11–13 rozdziału 17 opisują trzy rzeczy, których dziś nikt
nie pilnuje: nieustalony region bazy, narzędzie pomiarowe drukujące zawyżony zapas i drugi nośnik
treści karty poza bramką.

**Changelog v1.2 → v1.3 — trzy sprostowania jawne i jedna nowa decyzja. Zero zmian zakresu.**
Wszystkie trzy pozycje wykryto **pomiarem**, nie lekturą, i wszystkie trzy obalają przesłankę,
na której ten dokument stał. Stare brzmienia cytowane dosłownie — nigdy ciche przeredagowanie.

**S1 — warstwa sieciowa poprzednika: było „10 tras", jest 24.** v1.2 rozdział 9 otwierał się
zdaniem: *„**Stan poprzednika, zmierzony:** 10 tras — osiem odczytu, dwie zapisu. Funkcja zapisu
wpisu istnieje w silniku razem z transakcyjnością; **brakuje wyłącznie drogi HTTP do niej**.
Dlatego nowy interfejs był galerią, nie aplikacją."* **Pomiar 2026-08-29 na zbudowanym obiekcie
routera daje 24 trasy: 22 odczytu, 2 zapisu.** Nośnik planu nocnego (`docs/plan-nocy-2026-08-29.md`
§S1) twierdzi **26** — *„`api/router.py` ma dziś 1176 linii i 26 tras"* — **i to też jest nieprawda**;
wiążący jest pomiar niżej. Skutek dla zakresu prac opisany w rozdziale 9.1.

**S2 — stawka ryczałtu zaszyta w kodzie liczącym, wbrew regule „żadnej stawki w kodzie".**
Pozycja **nowa** — v1.2 jej nie znała. `../AI CFO/rdzen/formy.py` niesie literały stawek. Nośnik
planu (§S2) twierdzi, że *„to jedyny twardy literał stawki poza `stawki.py`"* — **pomiar pokazuje
pięć**, nie jeden, i dodatkowo **drugi nośnik tabeli progów składki zdrowotnej**. Ten drugi nośnik
**już się rozjechał z pierwszym**: przy przychodzie dokładnie 300 000 zł obie kopie liczą inaczej,
o **7 973,52 zł rocznie**, na korzyść ryczałtu. Kwot Darka nie dotyka. Rozpisane w rozdziale 8.4.

**S3 — typografia: krój z ramki, rozmiar 15 px. Nowa decyzja D-53.** Rozstrzygnięcie Darka
z 2026-08-29 godz. 00:55. Bramka „minimalny rozmiar tekstu **≥ 11 pt**" z rozdziału 12.2
**zostaje w mocy** — to jest zmiana wobec zapowiedzi w planie nocnym, który w liście ograniczeń
napisał: *„(Próg rozmiaru tekstu — odpuszczony, patrz S3.)"*. Nie jest odpuszczony. Szczegóły
w rozdziale 10.4, decyzja w 16, nowe pytanie otwarte **P11** w 16.1.

**Wymiar odniesienia ramki `Ksiegowanie.dc.html` — rozstrzygnięty.** Plan nocny (zadanie Z1)
podaje *„**1012 px wysokości przy 1440 px**"*; render z 2026-08-29 daje **972 px**. Wiążące jest
972 px — rozdział 10.4.

**Changelog v1.1 → v1.2 — zasilacze rejestru stawek: było trzy, są dwa. Decyzja Darka.**
v1.1 opisywała trzy zasilacze: czujkę aktów prawnych (ELI), **kontrolę GUS** i odczyt stron.
**Darek zdjął GUS 2026-08-29** słowami *„zostaw ten GUS, stawki można odczytać ze stron
internetowych ZUS-u"* — i miał rację potwierdzoną pomiarem: zmienna wynagrodzeniowa, którą
wybrałem (BDL 58787), **kończy się na 2008 roku**, więc kontrola waliłaby fałszywy alarm 214%
codziennie. Żywa seria istnieje (196229, do 2024), ale porównanie z danymi sprzed dwóch lat
i tak byłoby słabsze niż odczyt liczby wprost ze strony. **Moduł GUS usunięty z repozytorium.**
**Odczyt stron zbudowany i sprawdzony na żywo** (`wiedza/zrodla/strony.py`): podstawa 5 652 zł,
emerytalna 19,52%, rentowa 8,00%, chorobowa 2,45% — **zero rozjazdów z rejestrem**.
Aktualizacja rozdziału 7.3 i 7.1.

**Changelog v1.0 → v1.1 — jedno sprostowanie z pomiaru, zero zmian zakresu.**
Wersja v1.0 podawała **„około 26 tras"** i stawiała tę liczbę w rozdziale 17 jako pozycję
niezweryfikowaną — oszacowanie z inwentarza funkcji, nie z policzonej implementacji. Spis powstał
(`api/trasy.py`) i pomiar daje **36 tras: 15 odczytu, 21 zapisu**. Różnica bierze się stąd, że
inwentarz funkcji liczył ekrany, a nie operacje — jeden ekran Firma niesie pięć osobnych tras
zapisu (faktura, wpływ, koszt, danina zapłacona, forma). Poprawione w rozdziale 9 i skreślone
z listy niezweryfikowanych. **Sprostowanie jawne, nie ciche przeredagowanie** — stare brzmienie
zacytowane wyżej. Dopisane też odesłanie do `docs/plan-wydawania.md`, który od 2026-08-29 istnieje.

**Czym jest ten dokument.** PRD (product requirements document — dokument wymagań produktu) to
jedyny nośnik odpowiedzi na pytanie *„co ta aplikacja ma robić i po czym poznamy, że robi to
dobrze"*. Nie niesie kolejności prac — tę niesie `docs/plan-wydawania.md`. Nie powtarza treści
dokumentów źródłowych — **woła je**.

**Skąd się wziął.** Z burzy mózgów z Darkiem 2026-08-28 (godz. 23:2x–23:5x), z pomiarów na
poprzedniej aplikacji `../AI CFO` i z pięciu dokumentów, które już istniały i zostały odczytane
przed napisaniem pierwszego zdania: przekazanie do implementacji v1.9, kształt produktu doradcy,
fundament projektowy UI/UX, analiza Kruga, korekta produktu arkusz kontra aplikacja.

---

## 0. Jak czytać ten dokument — trzy zdania

Rozdziały **1–4** mówią, dla kogo to jest i po co; **5–9** opisują, jak to liczy; **10–11** opisują,
co widać na ekranie; **12** podaje bramki odbioru — czyli po czym poznać, że skończone. Rozdziały
**13–16** są dla tego, kto to odziedziczy: ryzyka, długi, decyzje zamknięte i pozycje, których
**nie zweryfikowano**.

Wszystko, co oznaczone **„niezweryfikowane"**, jest hipotezą i nie wolno tego cytować jako faktu.

---

## 1. Nastawy użytkownika — fakty, nie założenia

Pięć wartości, od których zależy każda kwota. Powtórzone tu z `CLAUDE.md` §2 świadomie, bo PRD bywa
czytany osobno — **nośnikiem rozstrzygającym jest CLAUDE.md**, ten rozdział go woła.

| Nastawa | Wartość |
|---|---|
| Forma opodatkowania 2026 i lata następne | **skala podatkowa** (zasady ogólne) |
| Składki ZUS | **duży ZUS**, pełne składki, z chorobową |
| VAT | czynny płatnik, 23%, **memoriałowo** (obowiązek z chwilą wystawienia faktury) |
| Data rozpoczęcia działalności | **2026-09-01**, wznowienie po zawieszeniu z 2023 |
| Horyzont danych | od IX 2026 w przód; 204 wpisy z 2025 wyłącznie jako historia |

**Pułapka jednostek — czytaj przed policzeniem czegokolwiek ze stóp procentowych.** Dwie stopy
są trzymane w dwóch różnych jednostkach: `zobowiazania.oprocentowanie` w **procentach** (9% = `9`),
`stawka_ryczaltu` w **ułamku** (9% = `0.09`). Pomnożenie kapitału przez `9` zamiast przez `0,09`
to błąd stukrotny.

---

## 2. Definicja produktu w jednym akapicie

> **Doradca Finansowy zamienia stan finansów jednoosobowej działalności w krótką, uszeregowaną
> listę konkretnych działań — każde z kwotą, z nazwanym rachunkiem i z nazwanym kosztem.**
> Odpowiada na trzy pytania: *czy mam pieniądze*, *co mnie zaraz uderzy*, *co mam z tym zrobić*.
> Wyłącznie o rzeczach, które da się odczytać z danych w aplikacji: płynności, poduszce, długu,
> podatkach i wykonaniu własnego planu. **Każdą liczbę i każdy próg liczy silnik; model językowy
> formułuje wokół nich zdanie i nie ma prawa dołożyć ani jednej cyfry.** Gdy czegoś nie wie —
> mówi, czego mu brakuje, zamiast pokazać zero.

Trzy słowa, których w tej definicji świadomie nie ma: **inwestycje**, **przepisy**, **rekomendacja**.

---

## 3. Użytkownik i moment użycia

**Jeden użytkownik.** Darek. Nie ma kont, ról ani izolacji danych między użytkownikami — i to jest
decyzja, nie przeoczenie. Konsekwencje wypisane w rozdziale 15.

**Moment użycia — zmierzony, nie założony.** Darek otwiera aplikację **przynajmniej raz dziennie**,
głównie po to, żeby **wpisać wydatek**. Cel jest motywacyjny (oszczędzanie, pilnowanie wydatków),
nie sprawozdawczy.

**Pięć pytań, w kolejności ich zadawania** — przełożenie czterech pytań Kruga na przypadek
człowieka, który zna swoją aplikację i otwiera ją po raz setny:

| Pytanie | Gdzie odpowiada | Jak szybko ma odpowiedzieć |
|---|---|---|
| Czy mam pieniądze? | Płynność — jedna liczba, największa rzecz na ekranie | **pierwsza sekunda** |
| Co mnie zaraz uderzy? | Płynność → Co mnie czeka | pierwsza sekunda: fakt; jedno kliknięcie: rozpis |
| Co mam z tym zrobić? | karta „Co mam zrobić" — jedno działanie z kwotą | pierwsza sekunda |
| Czy to, co widzę, jest aktualne? | stopka strażnika na każdym ekranie | pierwsza sekunda |
| Ile dziś wydałem i na co? | Księgowanie → Miesiąc | trzy dotknięcia do zapisu |

**Reguła twarda z tego wynikająca:** jeśli w pierwszej sekundzie nie widać, czy jest dobrze czy źle,
**ekran zawiódł — niezależnie od tego, jak poprawne są liczby niżej**.

**Telefon:** świadomie **poza v1**. Wszystkie jedenaście ramek jest zaprojektowanych na 1440 px;
ekran o szerokości 390 px to inny ekran, nie ten sam zmniejszony. Próg powrotu do tematu: **po
odbiorze v1**, jako osobny etap projektowy z własnymi ramkami. Do tego czasu aplikacja działa
z przeglądarki na komputerze, także spoza domu.

---

## 4. Zakres

### 4.1 W zakresie v1 — jedenaście tras

Decyzja Darka 2026-08-28: **cały zakres wchodzi do v1**, wydawany plasterkami z nazwanym pierwszym
momentem użyteczności.

| # | Miejsce | Pytanie, na które odpowiada |
|---|---|---|
| 1 | **Płynność** | Czy dam radę do końca okresu? |
| 2 | **Miesiąc** | Jak mi poszło w tym miesiącu? |
| 3 | **Budżet** | Co zaplanowałem i jak plan się trzyma? |
| 4 | **Raporty** | Ile wydałem na to przez dłuższy czas i na co poszło najwięcej? |
| 5 | **Firma** | Ile z tego, co zarobiłem, jest moje, a ile urzędu? |
| 6 | **Majątek** | Ile jestem wart i komu ile jestem winien? |
| 7 | **Godziny** | Czym się rozliczam — co i przez ile godzin robiłem? |
| 8 | **Doradca** | Zapytam o swoje pieniądze własnymi słowami. |
| 9 | **Ustawienia** | Jak ta aplikacja ma działać? |
| — | **Księgowanie** (akcja przy znaku słownym, nie pozycja paska) | Dopisz wydatek albo przychód — teraz, z każdego miejsca. |
| — | **Co mnie czeka** (rozwinięcie Płynności) | Co dokładnie nadejdzie do końca okna prognozy? |

**Księgowanie nie jest pozycją paska i to jest decyzja, nie przeoczenie.** Pasek odpowiada na
pytanie „gdzie jestem", księgowanie na „co robię". Ma jednak własny stan „tu jestem", bo od
2026-08-28 jest także miejscem.

### 4.2 Poza zakresem v1 — z jawnym powodem

| Co | Powód | Próg powrotu |
|---|---|---|
| Widok na telefonie | brak ramek na 390 px; to projekt, nie skalowanie | po odbiorze v1 |
| Powiadomienia (mail, systemowe) | każde dodatkowe powiadomienie obniża szansę reakcji na **którekolwiek** o 30% | gdy strażnik przez miesiąc znajdzie coś, czego Darek nie zauważył sam |
| Import wyciągu z banku | decyzja Darka: wpisywanie ręczne w trzy dotknięcia | gdy ręczne wpisywanie znów zamrze na miesiąc |
| Wielu użytkowników, konta, RODO | jeden człowiek | tylko przy decyzji o produkcie |
| Wystawianie faktur, księga przychodów i rozchodów | to robi księgowość | brak |
| Ulgi i wspólne rozliczenie z małżonkiem | **jawna luka** — tu skala wygrywa najmocniej | do rozstrzygnięcia po pierwszym rozliczeniu rocznym |

---

## 5. Mapa źródeł prawdy

Zasada: **jedna liczba ma jedno miejsce pochodzenia.** Poniższa tabela jest jej egzekucją.

| Rodzaj liczby | Skąd pochodzi | Kto nie ma prawa jej wytworzyć |
|---|---|---|
| Stawka podatku, składki, próg ustawowy | tabela `rejestr_stawek` (rozdz. 7) | silnik, interfejs, model językowy |
| Kwota wyliczona (zaliczka, składka, VAT) | `silnik/podatki.py` | trasa HTTP, interfejs, model językowy |
| Saldo prognozy, dzień pod kreską | `silnik/prognoza_plynnosci.py` | jak wyżej |
| Wykonanie planu, odchylenie | `silnik/budzet.py` | jak wyżej |
| Format kwoty, tytuł kafelka, napis | `silnik/prezentacja.py` | ekran (ma **wołać**) |
| Mapa ekranów i paska | `makiety/ekrany.py` | jak wyżej |
| Wygląd ekranu | `makiety/*.dc.html` + `paleta.json` | wykonawca interfejsu |

---

## 6. Model danych

Trzynaście tabel przeniesionych z poprzedniej aplikacji (schemat 11), plus jedna nowa
(`rejestr_stawek`). Nazwy zostają polskie, bez znaków diakrytycznych.

### 6.1 Zmiany typów wobec poprzednika

| Dziś (SQLite) | Po (PostgreSQL) | Co przez to znika |
|---|---|---|
| kwota jako `TEXT` `"1305.05"` | `NUMERIC(14,2)` | ręczne pakowanie każdej kwoty; baza sama pilnuje groszy |
| data jako `TEXT` | `DATE` | porównania dat na napisach, gdzie `"2026-9-1"` ≠ `"2026-09-01"` |
| `INTEGER 0/1` | `BOOLEAN` | pytanie „czy 0 znaczy nie, czy brak" |

### 6.2 Tabele

| Tabela | Co trzyma | Wierszy w danych wzorcowych |
|---|---|---|
| `wpisy_budzetu` | faktyczne wpisy: data, typ, kategoria, kwota, szczegóły | 204 (historia 2025) |
| `plan_budzetu` | plan miesiąca: rok, miesiąc, typ, kategoria, kwota, powtarzalność, dzień | 46 |
| `kategorie` | słownik: typ, nazwa, kolejność, aktywna | 24 |
| `przychody_jdg` | faktury sprzedażowe: numer, netto, VAT, data wystawienia, data zapłaty | 1 |
| `koszty_jdg` | koszty firmowe: netto, VAT do odliczenia | 0 |
| `godziny` | ewidencja czasu: data, rodzaj czynności, liczba godzin | 0 |
| `majatek` | aktywa: nazwa, kategoria, wartość | 2 |
| `zobowiazania` | długi: nazwa, kapitał, rata minimalna, oprocentowanie | 2 |
| `stan_konta` | odczyty salda: data → kwota (kotwica prognozy) | 1 |
| `cele_oszczednosciowe` | cele: nazwa, kategoria, kwota docelowa, termin | 1 |
| `forma_opodatkowania` | rok → forma (+ stawka ryczałtu, gdy dotyczy) | 1 |
| `ustawienia` | klucz → wartość | 2 |
| `przebiegi_straznika` | dziennik cichego strażnika | 0 |
| **`rejestr_stawek`** | **nowa** — stawki ustawowe z podstawą prawną (rozdz. 7) | zasilana |

### 6.3 Trzy nowe kolumny — każda z decyzji, nie z pomysłu

**1. `kategorie.niezbedna` (prawda/fałsz)** — czy kategoria liczy się do progu poduszki.
Bez niej próg poduszki jest **przedziałem 29 651–63 649 zł**, a nie liczbą. Domyślnie niezbędne:
`Kredyty`, `Czesne`, `PUWIS`, `Gaz`, `Telefon i Internet`, `Energia Elektryczna`, `Zdrowie`,
`Podatki i ZUS`. Elastyczne: `Jedzenie poza domem`, `Subskrypcje`, `Inne`.
**Do zaznaczenia przez Darka w Ustawieniach:** `Transport`, `Monika i Ada`, `Zakupy`
(w Zakupach siedzi jedzenie, które jest niezbędne, i reszta, która nie jest).

**2. `wpisy_budzetu.zrodlo`** — `historia-2025` albo `recznie`. Realizuje decyzję o 204 wpisach:
widoczne w Raportach, **niewidoczne dla prognozy i dla rachunku podatkowego**.
*Dlaczego to jest bramka poprawności, a nie metadana dla porządku:* bez niej „wgrać historię"
i „nie liczyć jej do podatku" są dwiema regułami w dwóch miejscach, które rozjadą się przy
pierwszej zmianie. Z nią jest **jedna reguła w jednym miejscu**: do rachunku podatkowego wchodzą
wyłącznie wiersze o źródle innym niż historia.

**3. `przychody_jdg.data_obowiazku_vat`** — data powstania obowiązku podatkowego w VAT.
Realizuje D-35 (memoriałowo). Dziś silnik sumuje VAT ze wszystkich faktur bez względu na okres —
to otwarta wada, opisana w rozdziale 13.

### 6.4 Czego świadomie nie ma

Tabeli użytkowników (jeden człowiek), tabeli sesji, historii kursów walut, tabeli inwestycji.

### 6.5 Migracja danych

Jednorazowy skrypt `migracja/z_sqlite.py`. **Bramka odbioru:** liczność po obu stronach zgadza się
tabela po tabeli **i** suma kontrolna kwot się zgadza. Nie „przepisałem i wygląda dobrze" — dwie
liczby, które muszą być równe. Kopia bazy źródłowej przed uruchomieniem.

---

## 7. Baza wiedzy o podatkach i ubezpieczeniach — rejestr stawek

**Wymaganie Darka z 2026-08-28:** *„aby wszystkie dane były prawdziwe musisz zbudować bazę wiedzy
o podatkach i ubezpieczeniach i podpiąć to jako źródło prawdy. Połącz się przez API ze stronami
rządowymi lub ZUS i aktualizuj bazę wiedzy."*

### 7.1 Co naprawdę istnieje — pomiar, nie założenie

Odczyt 2026-08-28, komendą `curl` z pomiarem czasu odpowiedzi:

| Źródło | Adres | Wynik | Co daje |
|---|---|---|---|
| **ELI Sejmu** | `api.sejm.gov.pl/eli` | **HTTP 200, 0,55 s** — 97 723 akty w Dz.U. | akty ze statusem obowiązywania, słowami kluczowymi, podstawą prawną, tekstem PDF |
| ~~GUS BDL~~ | `bdl.stat.gov.pl/api/v1` | HTTP 200, ale **wybrana seria kończy się na 2008 roku** | **odrzucone decyzją Darka 2026-08-29** — kontrola waliłaby fałszywy alarm 214% codziennie |
| **Biała lista VAT (MF)** | `wl-api.mf.gov.pl` | **HTTP 200, 0,17 s** | weryfikacja kontrahenta po numerze NIP |
| **ZUS** | `api.zus.pl` | **brak połączenia (HTTP 000)**; `zus.pl/…/api` → **404** | — |
| biznes.gov.pl, podatki.gov.pl | — | HTTP 200, ale `text/html` | strona do odczytu, nie interfejs programowy |

**Wniosek, wypowiedziany wprost: ZUS nie udostępnia publicznego interfejsu programowego ze
stawkami składek.** Polecenie „połącz się z ZUS przez API" nie da się wykonać dosłownie. Poniższa
konstrukcja jest obejściem — i jest **lepsza niż to, o co proszono**, z jednego powodu: zła stawka
ZUS to zły przelew do urzędu, nie zły piksel.

### 7.2 Kształt rejestru

Jedna tabela, z której silnik bierze **każdą** liczbę pochodzącą z prawa:

| Pole | Co niesie |
|---|---|
| `klucz` | np. `zus.podstawa_spolecznych`, `pit.prog_skali`, `vat.stawka_podstawowa` |
| `wartosc` | `NUMERIC` |
| `jednostka` | `zl` / `ulamek` / `procent` — **zamyka pułapkę jednostek z rozdz. 1** |
| `obowiazuje_od`, `obowiazuje_do` | okres obowiązywania; `do` puste = nadal obowiązuje |
| `podstawa_prawna` | adres ELI aktu (np. `DU/2025/1874`) albo adres strony |
| `zrodlo_url`, `data_odczytu` | skąd i kiedy odczytano |
| `zatwierdzil`, `data_zatwierdzenia` | **kto to potwierdził** — bez tego stawka nie wchodzi do rachunku |
| `status` | `zatwierdzona` / `proponowana` / `wycofana` |
| `niezweryfikowane` | jawna notatka o wątpliwości (np. rozjazd między dwoma źródłami) |

**Silnik czyta wyłącznie wiersze `zatwierdzona`.** Wiersz `proponowana` jest widoczny w interfejsie
jako propozycja i nie wchodzi do żadnej kwoty.

### 7.3 Dwa zasilacze

*(v1.1 opisywała trzy — kontrola GUS zdjęta decyzją Darka 2026-08-29, patrz changelog.)*

**1. Czujka aktów prawnych (ELI).** Raz dziennie pyta o akty ze słowami kluczowymi `składki`,
`ubezpieczenia społeczne`, `podatek dochodowy`, `podatek od towarów i usług`, o dacie ogłoszenia
późniejszej niż ostatnie sprawdzenie. Trafienie → chorągiewka w aplikacji: *„stawki mogą być
nieaktualne — Dz.U. 2026 poz. N, tytuł, odsyłacz do tekstu"*. **Nie zmienia żadnej wartości.**

**2. Odczyt stron** (`wiedza/zrodla/strony.py`, zbudowany i sprawdzony 2026-08-29).
`biznes.gov.pl` i `zus.pl` wyciągają **konkretną liczbę**, bo API jej nie poda. Odczyt porównuje
wartość z rejestrem i zgłasza różnicę; **nigdy jej nie wpisuje**. Łapie też przypadek, którego
czujka aktów nie złapie: stawkę, która **cicho się zestarzała**, bo zmianę ogłoszono obwieszczeniem
bez nowego aktu.

Trzy zasady konstrukcyjne, każda zamyka konkretną awarię:
- **Kotwica na frazie, nie na pozycji.** Reguła szuka *„na ubezpieczenie emerytalne – 19,52%
  podstawy"*, nie *„trzeciej liczby na stronie"*. Przestawienie akapitu przez redakcję ZUS nie ma
  prawa podmienić stopy emerytalnej na rentową.
- **Brak trafienia to błąd, nie zgoda.** Reguła, która nic nie znalazła, przerywa odczyt. Zwrócenie
  „brak zmian" byłoby sprawdzeniem, do którego nic nie dociera — a takie sprawdzenie **melduje
  sukces**.
- **Zero zapisu.** Moduł zwraca rozjazdy i nie ma funkcji piszącej do rejestru; pilnuje tego
  strażnik `test_odczyt_NIE_MA_drogi_do_zapisu_w_rejestrze`.

**Pomiar 2026-08-29 na żywej stronie:** podstawa **5 652 zł**, emerytalna **19,52%**, rentowa
**8,00%**, chorobowa **2,45%** — **zero rozjazdów** z rejestrem początkowym.

### 7.4 Reguła twarda: automat proponuje, człowiek zatwierdza

Żaden z trzech zasilaczy nie podmienia stawki używanej do rachunku. Każdy tworzy wiersz
`proponowana` i pokazuje w Ustawieniach: **stara wartość → nowa → źródło → data**. Darek
zatwierdza jednym kliknięciem, co wpisuje jego podpis i datę.

**Powód nie jest teoretyczny.** Równoległa wersja tej aplikacji miała czujkę aktów prawnych, która
**przy awarii API zwracała akty zmyślone, nieodróżnialne od prawdziwych**. Automat wpisujący
stawkę zamienia taką awarię w zły przelew do ZUS. To jest też zgodne z konstytucją firmy §7:
gdzie ocena maszyny wychodzi na zewnątrz jako podstawa działania, ostatnie słowo ma człowiek.

### 7.5 Co przestanie działać, gdy padnie API

**Nic z rachunku.** Aplikacja liczy z ostatnio zatwierdzonych stawek i pokazuje datę ostatniego
udanego sprawdzenia. Traci wyłącznie **zdolność wykrycia, że coś się zmieniło** — i mówi o tym
wprost: „ostatnie sprawdzenie stawek: 14 dni temu, nieudane". Awaria do stanu użytecznego.

### 7.6 Zasilenie początkowe

Rejestr startuje z wartościami przeniesionymi z `../AI CFO/rdzen/stawki.py` (odczyt 2026-08-25,
źródło biznes.gov.pl), **każda z podstawą i datą**, wszystkie w statusie `proponowana` do
pierwszego zatwierdzenia przez Darka. Wartości niosące znaną wątpliwość wchodzą z wypełnionym
polem `niezweryfikowane` — w szczególności limit odliczenia składki zdrowotnej, który
podatki.gov.pl przypisuje do 2026, a biznes.gov.pl do 2025.

### 7.7 Czerwona linia — odnotowane

Podpięcie zewnętrznego źródła danych jest czerwoną linią konstytucji firmy (§4). **Sign-off Darka
padł w poleceniu z 2026-08-28.** Whitelist: `api.sejm.gov.pl`, `bdl.stat.gov.pl`,
`wl-api.mf.gov.pl`, `biznes.gov.pl`, `zus.pl`. Wszystkie są publiczne, wszystkie służą wyłącznie
odczytowi, żadne nie dostaje danych Darka.

---

## 8. Silnik — reguły rachunku

### 8.1 Co przenosi się bez zmian

`podatki.py` (skala, składki, VAT, zaliczka), `terminy.py`, `prognoza_plynnosci.py`, `budzet.py`,
`majatek.py`, `okres.py`, `prezentacja.py`, `weryfikacja.py`. Wraz ze strażnikami.

### 8.2 Reguły rachunku — te, które wolno złamać tylko przez pomyłkę

| Reguła | Dlaczego tak |
|---|---|
| **Każdy składnik składek ZUS zaokrągla się osobno** | tak nalicza ZUS; suma niezaokrąglonych daje 1 926,77 zamiast **1 926,76** — grosz różnicy |
| **Podstawa składki zdrowotnej zaokrągla się przed naliczeniem 9%** | tak liczy ZUS: `9 228,64 × 0,60 = 5 537,184 → 5 537,18`, dopiero potem `× 0,09` |
| **Podatek zaokrągla się do pełnych złotych** | art. 63 Ordynacji podatkowej |
| **Pozostałe kwoty do groszy, w górę od połowy** | |
| **VAT liczy się memoriałowo** | D-35: obowiązek z chwilą **wystawienia** faktury. Faktura wystawiona 5 X za wrzesień należy do okresu **październik**, termin **25 XI** |
| **Termin daniny nie może wypaść przed rozpoczęciem działalności** | naprawiona wada: przy odczycie 15 IX wszystkie daniny wychodziły „za sierpień", czyli za miesiąc, w którym działalności nie było |
| **Kwota wymagalna na termin to składki narastająco minus zapłacone** | otwarta wada: dziś na jeden termin spada suma za dwa okresy — ZUS pokazuje 5 120,65 zł tam, gdzie wymagalne jest 2 359,30 zł |
| **Oś prognozy dzieli się na dniu dzisiejszym** | D-20: dni minione liczą się z **rzeczywistych wpisów**, dni przyszłe z **planu**. Dziś oś powstaje wyłącznie z planu, więc kto wydał ponad plan, widzi sytuację lepszą niż jest |
| **Nadwyżka wydatku ponad plan pomniejsza kwotę do dyspozycji; nadwyżka przychodu jej nie powiększa** | D-9, asymetria świadoma. Nie „naprawiaj" tego przez dodanie symetrii |
| **Kotwica prognozy pochodzi z odczytu salda, nigdy z sumy aktywów** | odczyt niesie **datę**, majątek nie. Wyprowadzenie kotwicy z majątku kazałoby datę zmyślić i prognoza udawałaby świeżość każdego dnia |
| **Poduszka finansowa to osobna kategoria** | D-36: żaden rachunek nie jest poduszką z nazwy. Rachunek bieżący to pieniądze na bieżące życie, konto oszczędnościowe jest na inne cele |
| **Próg poduszki = 6 × miesięczne wydatki niezbędne** | decyzja Darka 2026-08-28. Liczony, nie wpisywany — rozstrzygnięcie sprzeczności z rozdz. 10.3 |
| **Kosz przy pozycji planu kończy regułę, nie kasuje historii** | obowiązuje od bieżącego miesiąca w przód. Funkcja kasująca istnieje w silniku i jest **świadomie odcięta** od interfejsu; strażnik tego pilnuje. Nowa aplikacja ma to zachowanie **przejąć, nie naprawić** |

### 8.3 Cztery długi przeniesione z poprzednika — do naprawy, nie do odziedziczenia

| Dług | Co jest zepsute | Skutek dla użytkownika |
|---|---|---|
| Miejsca ryczałtowe | cztery miejsca liczą i mówią ryczałtem bezwarunkowo | aplikacja podaje kwoty wyliczone formą, której Darek nie ma |
| Kwota zbiorcza na jeden termin | patrz tabela wyżej | ZUS pokazuje ponad dwukrotność kwoty wymagalnej |
| VAT bez daty faktury | sumuje VAT ze wszystkich faktur bez względu na okres | kwota siedzi w złym okresie |
| Oś prognozy bez wpisów | patrz tabela wyżej | przekroczenie planu nie widać w prognozie |

**Od v1.3 długów jest pięć, nie cztery** — piąty opisany niżej. Nagłówek tego podrozdziału mówi
„cztery", bo tak brzmiał w v1.2 i tak został znaleziony; liczbę prostuje 8.4.

### 8.4 Piąty dług — stawki zaszyte w kodzie liczącym (sprostowanie S2, nowe w v1.3)

Reguła `CLAUDE.md` §3.3 brzmi: **żadnej stawki w kodzie** — każda liczba pochodząca z ustawy,
rozporządzenia albo komunikatu ZUS mieszka w rejestrze stawek. Pomiar 2026-08-29 pokazuje, że
poprzednik łamie ją w **jednym module**, ale w **pięciu miejscach**, nie w jednym.

```bash
cd "../AI CFO" && grep -n 'Decimal("0.085")\|Decimal("0.15")\|mnoznik = Decimal' rdzen/formy.py
```

Wyjście (2026-08-29):

```
 91:        mnoznik = Decimal("0.60")
 93:        mnoznik = Decimal("1.00")
 95:        mnoznik = Decimal("1.80")
160:        _ryczalt(przychod, Decimal("0.085"), spoleczne, miesiecy,
162:        _ryczalt(przychod, Decimal("0.15"), spoleczne, miesiecy,
```

Pełne otoczenie (`sed -n '89,95p' rdzen/formy.py`, odczyt 2026-08-29):

```
    # Próg zdrowotnej wg przychodu rocznego — ta sama tabela co w rdzen.podatki.
    if przychod < Decimal("60000"):
        mnoznik = Decimal("0.60")
    elif przychod <= Decimal("300000"):
        mnoznik = Decimal("1.00")
    else:
        mnoznik = Decimal("1.80")
```

| # | Miejsce | Liczba | Co to jest |
|---|---|---|---|
| 1 | `rdzen/formy.py:160` | `Decimal("0.085")` | stawka ryczałtu 8,5% dla usług informatycznych |
| 2 | `rdzen/formy.py:162` | `Decimal("0.15")` | stawka ryczałtu 15% |
| 3–5 | `rdzen/formy.py:90–95` | `60000`, `300000`, `0.60`/`1.00`/`1.80` | progi i mnożniki podstawy składki zdrowotnej |

**Nośnik twierdzi X, pomiar pokazuje Y.** `docs/plan-nocy-2026-08-29.md` §S2 podaje jedno miejsce
i nazywa je jedynym: *„`rdzen/formy.py:160` niesie literał `Decimal("0.085")` przekazany do
`_ryczalt(...)`. To jedyny twardy literał stawki poza `stawki.py`."* **Miejsc jest pięć.**

**Pozycje 3–5 są dodatkowo drugim nośnikiem tej samej reguły**, co reguła „żadna liczba nie
powstaje w dwóch miejscach" (`CLAUDE.md` §3.2) czyni osobną wadą. Ta sama tabela stoi już
w rejestrze stawek silnika:

```bash
cd "../AI CFO" && grep -n '60000\|300000\|1\.80' rdzen/stawki.py rdzen/formy.py
```

```
rdzen/stawki.py:66:    ProgZdrowotnej(Decimal("0"), Decimal("60000"), Decimal("0.60")),
rdzen/stawki.py:67:    ProgZdrowotnej(Decimal("60000"), Decimal("300000"), Decimal("1.00")),
rdzen/stawki.py:68:    ProgZdrowotnej(Decimal("300000"), None, Decimal("1.80")),
rdzen/formy.py:90:    if przychod < Decimal("60000"):
rdzen/formy.py:92:    elif przychod <= Decimal("300000"):
rdzen/formy.py:95:        mnoznik = Decimal("1.80")
```

Sam kod to przyznaje — komentarz w linii 89, zacytowany wyżej: *„Próg zdrowotnej wg przychodu
rocznego — ta sama tabela co w rdzen.podatki."*. Kopia **oznaczona i nadal kopia**: bez strażnika
i bez progu konsolidacji, czyli dług ukryty, nie decyzja.

**I te kopie już się rozjechały — zmierzone, nie przewidziane.** Porównanie nośnika
(`podatki.prog_dla_przychodu`, czytającego `stawki.PROGI_ZDROWOTNEJ`) z kopią w `formy.py`,
punkt po punkcie na granicach przedziałów:

```bash
cd "../AI CFO" && .venv/bin/python3 -c "
from decimal import Decimal
from rdzen import stawki, podatki
for p in ['59999.99','60000','60000.01','299999.99','300000','300000.01']:
    x = Decimal(p)
    a = stawki.PROGI_ZDROWOTNEJ[podatki.prog_dla_przychodu(x)-1].mnoznik
    if x < Decimal('60000'): b = Decimal('0.60')
    elif x <= Decimal('300000'): b = Decimal('1.00')
    else: b = Decimal('1.80')
    print(f'{p:>12} | {a:>12} | {b:>12} | {\"ROZJAZD\" if a!=b else \"zgodne\"}')"
```

Kolumna druga to **nośnik** (funkcja silnika `podatki.prog_dla_przychodu`, czytająca
`stawki.PROGI_ZDROWOTNEJ`), kolumna trzecia to **kopia** przepisana wprost z `formy.py:90–95`.
Wyjście, odczyt 2026-08-29:

```
    59999.99 |         0.60 |         0.60 | zgodne
       60000 |         1.00 |         1.00 | zgodne
    60000.01 |         1.00 |         1.00 | zgodne
   299999.99 |         1.00 |         1.00 | zgodne
      300000 |         1.80 |         1.00 | ROZJAZD
   300000.01 |         1.80 |         1.80 | zgodne
```

**Przy przychodzie dokładnie 300 000 zł te dwa miejsca liczą inaczej.** Nośnik używa ostrego
porównania („mniej niż górny limit"), kopia użyła nieostrego („nie więcej niż") — jedna literka
różnicy. Cena tej literki, wyliczona funkcją silnika `stawki.skladka_zdrowotna`:
**1 495,04 zł wobec 830,58 zł miesięcznie, czyli 664,46 zł na miesiąc i 7 973,52 zł na rok.**
Kierunek błędu jest niekorzystny: **porównanie form pokazuje ryczałt tańszym, niż wynika z reguły
zapisanej w silniku.** Kwot Darka to nie dotyka (skala, przychód poniżej progu), ale to jest
**dokładnie ta awaria, przed którą chroni reguła „jedna liczba, jedno miejsce"** — i została
znaleziona przez porównanie kopii, nie przez test. Żaden strażnik jej nie pilnował.

**Czy to dotyka kwot Darka: nie.** Wszystkie pięć literałów żyje w funkcji porównującej formy
opodatkowania — a Darek jest na skali (rozdział 1). Zmiana stawki ryczałtu przez ustawodawcę
zepsułaby **porównanie**, nie **rachunek**. To obniża pilność, nie znosi wady.

**Co z tym robimy — zadanie Z4 (przeniesienie silnika):**
1. Pozycje 1–2 wchodzą do rejestru stawek pod kluczami `ryczalt.stawka_uslugi_it` (8,5%)
   i `ryczalt.stawka_15` (15%), w jednostce `ulamek`, z podstawą prawną i datą odczytu.
2. Pozycje 3–5 **znikają z `formy.py`** — moduł woła istniejącą funkcję
   `podatki.prog_dla_przychodu`, zamiast powtarzać tabelę. To zamyka przy okazji rozjazd na progu
   300 000 zł zmierzony wyżej. **Strażnik obowiązkowy:** test porównujący obie ścieżki na
   granicach przedziałów (59 999,99 / 60 000 / 300 000 / 300 000,01), z mutacją — dziś taki test
   **padłby na wartości 300 000**, co jest gotowym dowodem, że strzeże.
3. Bramka rozdziału 12.1 *„Każda stawka pochodzi z rejestru — zero trafień poza `wiedza/`"*
   dostaje strażnika, który dziś **zaczerwieniłby się na tych pięciu miejscach**. Do czasu jego
   napisania ta bramka jest **niepotwierdzona testem** — etykieta jawna, nie domysł.

---

## 9. Warstwa sieciowa

*(Rozdział przepisany w v1.3 — sprostowanie S1. Stare brzmienie zacytowane w changelogu na górze.)*

### 9.1 Stan poprzednika — 24 trasy, nie 10 i nie 26

**Pomiar 2026-08-29, na zbudowanym obiekcie routera, nie wyszukiwaniem tekstu.** Router (obiekt
zbierający trasy HTTP — adresy, pod którymi aplikacja odpowiada) jest źródłem rozstrzygającym,
bo to on faktycznie obsługuje ruch; wyszukiwanie tekstu opisuje jedynie zapis w pliku.

```bash
cd "../AI CFO" && .venv/bin/python3 -c "
from api.router import zbuduj_router
from collections import Counter
r = zbuduj_router()
trasy = [(sorted(m for m in x.methods if m not in ('HEAD','OPTIONS')), x.path) for x in r.routes]
for m, p in trasy: print(m[0], p)
print('RAZEM:', len(trasy))
print(Counter(m[0] for m, p in trasy))"
```

Wyjście, odczyt 2026-08-29 — pełne, nieskrócone:

```
GET /api/stan
GET /api/prognoza
GET /api/kotwica
PUT /api/kotwica
GET /api/ustawienia/prognoza
PUT /api/ustawienia/prognoza
GET /api/wolne-srodki
GET /api/co-mnie-czeka
GET /api/straznik
GET /api/okres
GET /api/miesiac
GET /api/budzet
GET /api/budzet/plan
GET /api/budzet/cele
GET /api/budzet/historia
GET /api/raporty
GET /api/firma
GET /api/firma/faktury
GET /api/firma/koszty
GET /api/majatek
GET /api/godziny
GET /api/doradca
GET /api/ustawienia
GET /api/ustawienia/kategorie
RAZEM: 24
Counter({'GET': 22, 'PUT': 2})
```

Plik ma **1176 linii** (`wc -l api/router.py` → `    1176 api/router.py`). Osobno, poza tym rachunkiem, `api/statyka.py`
niesie **3 trasy serwujące pliki** (`/nowy`, `/nowy/`, `/nowy/{sciezka:path}`) — nie są to trasy
danych i nie wchodzą do liczby 24.

**Uwaga metodologiczna — dlaczego pomiar nie jest wyszukiwaniem tekstu.** Pierwsze wyszukanie
wzorca `@router.` / `@app.` zwróciło **zero trafień**, choć trasy istnieją: w tym pliku zmienna
routera nazywa się `trasy`, a dekoratory (linijki `@…` przypinające funkcję do adresu) są wcięte
wewnątrz funkcji budującej. **Zero trafień nie znaczy „nie ma"** — znaczy „szukałem nie tego".
Sprawdzone dodatkowo, że żaden dekorator nie jest zapisany w wielu linijkach (wyszukanie linii
z dekoratorem bez zamykającego nawiasu daje pustkę), więc liczba z wyszukiwania i liczba
z obiektu routera **zgadzają się na 24** — kontrola dwustronna.

**Nośnik twierdzi X, pomiar pokazuje Y — dwa razy.** v1.2 tego dokumentu twierdziła **10**;
`docs/plan-nocy-2026-08-29.md` §S1 twierdzi **26**; pomiar daje **24**. Skąd „10": opis commita
`dfcc702` brzmi *„AI CFO krok 2.2 czesciowo: trasy odczytu 10 -> 24"* — liczba 10 była prawdziwa
**przed** tym commitem i zestarzała się, nie została zmyślona. Pomiar konfiguracji ma termin
ważności.

**Drugi nośnik tej samej nieprawdy — do usunięcia w zadaniu Z6.** Docstring (komentarz nagłówkowy)
pliku `api/trasy.py` **w tym projekcie** powtarza zdanie *„STAN POPRZEDNIKA, ZMIERZONY: 10 tras —
osiem odczytu, dwie zapisu"*. To druga kopia obalonej przesłanki; przy przepisywaniu tras ma zostać
zastąpiona odesłaniem do tego rozdziału.

### 9.2 Co z tego wynika dla zakresu prac

**Backend poprzednika jest znacznie bardziej zbudowany, niż zakładała v1.2.** Praca nad nową
aplikacją ma go **przenieść i uzupełnić**, a nie pisać od zera.

**Teza „nowy interfejs był galerią" zostaje prawdziwa co do skutku — ale przyczyna jest inna.**
Nie ma gdzie wpisać wydatku, to fakt. Powodem nie jest jednak brak tras w ogóle, tylko **brak
ekranów**: z 24 tras **22 to odczyt**, a jedyne dwa zapisy dotyczą kotwicy prognozy
(`PUT /api/kotwica`) i nastaw prognozy (`PUT /api/ustawienia/prognoza`). **Drogi HTTP do dopisania
wpisu budżetowego faktycznie nie ma** — ta część zdania z v1.2 broni się w pomiarze.

### 9.3 Spis tras nowej aplikacji — 36, i to jest plan, nie stan

**Zmierzone: 36 pozycji — 15 odczytu, 21 zapisu** (`api/trasy.py` w tym projekcie; odczyt
2026-08-29: `len(WSZYSTKIE)=36`, `len(ODCZYT)=15`, `len(ZAPIS)=21`). **To spis tego, co warstwa
sieciowa ma udostępniać** — lista do zbudowania, nie liczba tras działających. Nie mylić
z pomiarem 24 z rozdziału 9.1, który opisuje **poprzednią** aplikację.

Pogrupowane po ekranach. Obowiązkowo komplet **czterech operacji**,
bez których nie da się wyłączyć starej zakładki: dodać wpis · wycofać wpis · ustawić pozycję
planu · **zakończyć** pozycję planu.

### 9.4 Dwie zasady, obie z pomiaru

1. **Jeden piszący na jeden obszar.** Złamanie tej reguły w poprzedniej aplikacji dało zmierzone
   **400 prób → 274 wiersze**, wpisy zdublowane.
2. **Zero rachunku w warstwie sieciowej.** Trasa woła silnik i zwraca wynik. Kwota policzona
   w trasie jest drugim nośnikiem reguły.

**Kwoty w odpowiedzi jako napis, nie jako liczba zmiennoprzecinkowa.** Zamiana `Decimal` na `float`
w warstwie sieciowej gubi grosze i **zwraca 200** — awaria bezgłośna, zmierzona u poprzednika.

---

## 10. Interfejs

### 10.1 Reguła nadrzędna — makieta jest wiążąca w dwóch wymiarach

**Zakres:** każda funkcja widoczna na ramce `makiety/*.dc.html` wchodzi do aplikacji.
**Wygląd:** odwzorowanie zgodne co do piksela przy tej samej szerokości.
Ekran jest skończony, gdy **porównanie maszynowe zrzutu z ramką przechodzi** — nie gdy „wygląda
tak samo". Odstępstwo wymaga zgody Darka i wpisu tutaj.

**Wspólne dla wszystkich jedenastu ekranów:** znak słowny + akcja `Księgowanie` obok niego ·
pasek dziewięciu pozycji · data i godzina odczytu · **stopka strażnika** („Ostatnie sprawdzenie:
dziś 06:00 — nic pilnego nie znalazł") · przełącznik okresu tam, gdzie okres ma znaczenie.

### 10.2 Inwentarz funkcji — odczytany z ramek

| Ekran | Funkcje |
|---|---|
| **Płynność** | księga dzień·pozycja·kwota·saldo · wykres z trzema punktami odniesienia (dziś, dzień pod kreską, koniec okna) · saldo minimalne z podpisem „NAJNIŻEJ" · zdanie wyjaśniające przyczynę · wejście „Co mnie czeka — N pozycji" · okno 45 dni · **karta „Co mam zrobić" (nowa, patrz 11.2)** |
| **Miesiąc** | pięć kafelków: Przychody · Wydatki · Oszczędności · Poduszka finansowa · **Zarezerwowane na zaplanowane wydatki** · „Na co poszły pieniądze" · wykres salda narastającego · **linia przerywana = brak przepływu, nie brak danych** |
| **Budżet** | trzy kafelki planu + bilans planu · plan kontra wykonanie z odchyleniem, największe u góry · dodaj pozycję planu · **skopiuj z poprzedniego miesiąca** · cele oszczędnościowe z postępem i tempem · historia z poprawianiem i wycofywaniem zaznaczonych |
| **Raporty** | ranking kategorii: wpisów · suma · udział · plan · odchylenie · trzy zakładki typu · rozwijanie kategorii do wpisów · **stan pusty zamiast danych przykładowych** z wejściem „Dopisz pierwszy wydatek" |
| **Firma** | forma i data działalności + rejestr stawek ze źródłem · daniny do zapłacenia z terminem i przyciskiem „Zapłacone" · faktury sprzedażowe + „Nowa faktura" + znacznik wpływu · **rozbicie faktury na siedem pozycji** (netto → VAT → składki społeczne → dochód → zdrowotna → zaliczka PIT → zostaje do dyspozycji) · „na jakich założeniach stoi to wyliczenie" · koszty firmowe + „Dodaj koszt" |
| **Majątek** | wartość netto + pokrycie zobowiązań w procentach · aktywa z udziałem · zobowiązania z ratą i oprocentowaniem · dodaj aktywo / zobowiązanie · suma rat · **podpowiedź „podaj oprocentowanie, nigdy 0%: zero jest odpowiedzią, pustka jej brakiem"** |
| **Godziny** | stawka godzinowa · zakres okresu · dodaj godziny (data, liczba, rodzaj, opis) · wpisy w okresie · „ile z tego wychodzi" · **zdanie o skali zamiast tabeli PKWiU** |
| **Doradca** | rozmowa · **„Policzone narzędziami" z nazwami użytych narzędzi** · podpowiedzi pytań · lista dwunastu narzędzi z wyjaśnieniem, skąd biorą się liczby |
| **Ustawienia** | słownik kategorii z licznikiem wpisów i znacznikiem „systemowa" · nowa kategoria per typ · **zaznaczenie „niezbędna"** · import z arkusza · **gdzie leżą dane** (przeprojektowane, patrz 10.3) · **rejestr stawek z zatwierdzaniem propozycji** (nowe) · motyw jasny/ciemny · „Czego tu nie ma" z odesłaniami |
| **Księgowanie** | trzy typy wpisu · data · kwota **bez znaku** („minus jest w typie wpisu") · szczegóły nieobowiązkowe · kategoria z listy · **„Co ruszy ten wpis" — podgląd trzech liczb przed i po** · ostatnie wpisy z „wycofaj" przez sześć pozycji |
| **Co mnie czeka** | pozycje z „za N dni" · saldo po każdym dniu · odłożone na daniny |

**Trzy elementy z tej listy to mechanizmy uczciwości, nie ozdoby** — i to one najczęściej giną przy
„odwzorowaniu wyglądu":

1. **Linia przerywana** na wykresie miesiąca — odróżnia „nic się nie działo" od „nic nie wiem".
2. **„Co ruszy ten wpis"** na Księgowaniu — pokazuje skutek **przed** zapisem, więc pomyłka jest
   widoczna, zanim wejdzie do bazy.
3. **„Policzone narzędziami"** u Doradcy — każda kwota ma podpisane źródło.

### 10.3 Trzy sprzeczności ramek — rozstrzygnięte

Skoro makiety są wiążące, ich wzajemne rozbieżności przestają być drobiazgiem.

**S-1. VAT — dwie ramki mówią co innego.** `Firma.dc.html`: *„VAT za wrzesień, 2 576,00 zł,
do 26.10.2026"*. `Doradca.dc.html`: *„VAT z faktury 1/2026, 2 576,00 zł, do 25.11"*. Faktura jest
wystawiona 5 X. **Rozstrzygnięcie: rację ma Doradca** — D-35 (memoriałowo) daje okres październik
i termin 25 XI. **Ramka `Firma.dc.html` niesie starą arytmetykę i wymaga poprawki przed budową.**

**S-2. Poduszka ma dwa progi.** `Budzet.dc.html` pokazuje cel *„Poduszka finansowa 30 000,00 zł"*
wpisany ręcznie; decyzja z 2026-08-28 mówi: próg = 6 × wydatki niezbędne, czyli **liczony**.
**Rozstrzygnięcie: próg jest liczony.** Pole celu pokazuje wynik rachunku i wolno go nadpisać
świadomie — z widoczną informacją, że wartość jest nadpisana ręcznie i ile wynosi rachunek.
Jeden nośnik, drugi jawnie oznaczony jako odstępstwo.

**S-3. Ustawienia mówią „dane wyłącznie na tym komputerze".** Ramka niesie ścieżkę do pliku bazy
i zdanie o lokalności. Po decyzji o chmurze **to zdanie stanie się nieprawdą**, a aplikacja
mówiąca nieprawdę o tym, gdzie leżą finanse użytkownika, jest gorsza niż aplikacja, która milczy.
**Rozstrzygnięcie: sekcja wymaga przeprojektowania** — co leży w chmurze, u kogo, w jakim kraju,
jak robione są kopie zapasowe, jak wyeksportować wszystko na dysk. Podobnie „Import z arkusza"
ze ścieżką w iCloud staje się **wgraniem pliku**.

### 10.4 Typografia i wymiary odniesienia — zmierzone (sprostowanie S3, nowe w v1.3)

**Rozstrzygnięcie Darka 2026-08-29, godz. 00:55:** *„sama wielkość tekstu może być 15 px, reszta
zostaje bez zmian"* — po wcześniejszym *„ma wyglądać idealnie jak tutaj"* (godz. 00:44).
Zapisane jako **D-53**.

**Trzy ustalenia:**
1. **Krój wraca do ramki.** `-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
   Arial, sans-serif`. Szeryfowy `ui-serif Georgia` (krój z poprzeczkami przy literach, jak
   w książce) był dodatkiem wykonawcy, nie decyzją, i schodzi.
2. **Rozmiar podstawowy zostaje 15 px = 11,25 pt.** Bramka *„minimalny rozmiar tekstu ≥ 11 pt"*
   z rozdziału 12.2 jest nim **spełniona i zostaje w mocy**. To jest zmiana wobec zapowiedzi
   w planie nocnym, który w liście ograniczeń napisał: *„(Próg rozmiaru tekstu — odpuszczony,
   patrz S3.)"*. **Nie jest odpuszczony.**
3. **Wszystko pozostałe co do piksela z ramki.**

**Stan wykonania — zmierzony, nie zadeklarowany.** Krok wykonany w kodzie (commit `72e7ff3`).

```bash
grep -n "font:" interfejs/app/powloka.css
```

```
26:  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI",
27:        "Helvetica Neue", Arial, sans-serif;
```

**Znalezisko z pomiaru ramek — krój szeryfowy w ramce jednak jest, tylko nie tam, gdzie szukano.**
Nośnik (plan nocny) twierdzi: *„Typografia ramek: bezszeryfowa `-apple-system`, podstawa 13 px."*
Pomiar pokazuje **dwa kroje w każdej ramce**: bezszeryfowy na `body` i **szeryfowy `'Iowan Old
Style', 'Palatino Linotype', Palatino, 'Times New Roman', Times, serif` na kwotach**, razem
z `font-variant-numeric: tabular-nums` (cyfry o równej szerokości, żeby kwoty stały w kolumnie).

Zliczenie wystąpień rodziny `Iowan Old Style` w każdym z 41 plików `makiety/*.dc.html`
(odczyt 2026-08-29) — cztery wiersze z wyjścia plus podsumowanie:

```
Budzet.dc.html: 15
Firma.dc.html: 14
Ksiegowanie.dc.html: 8
Ustawienia.dc.html: 25
ramek z szeryfem: 37 z 41
```

**Konsekwencja dla wykonawcy ekranu:** `interfejs/app/powloka.css` niesie dziś **wyłącznie krój
bezszeryfowy**. Kwoty wyrenderowane bezszeryfowo **nie zejdą się z ramką** i bramka odwzorowania
(12.7) to zobaczy. Krój kwot ma zostać przeniesiony z ramki razem z resztą — to nie jest ozdoba,
to część wiążącej specyfikacji wyglądu.

**Wymiar odniesienia ramki `Ksiegowanie.dc.html` — rozstrzygnięty.** Plan nocny (zadanie Z1)
podaje *„1012 px wysokości przy 1440 px"*. Render z 2026-08-29:

```bash
cd "../AI CFO/docs/makiety-v2" && ../../.venv/bin/python3 render.py \
  "../../../Doradca Finansowy/makiety/Ksiegowanie.dc.html" /tmp/kontrola-ksiegowanie.png
```

```
{"doc": 972, "wezlow": 138, "tekstow": 74}
```

Powtórzone dwukrotnie, ten sam wynik; plik wyjściowy `PNG image data, 1440 x 972`.

| Wymiar odniesienia dla zadania Z1 | Wartość |
|---|---|
| Szerokość × wysokość dokumentu | **1440 × 972 px** |
| Liczba węzłów | **138** |
| Liczba tekstów | **74** |

**Wiążące jest 972 px, nie 1012 px.** Liczba tekstów **74**, nie 64 — obie liczby z planu
i z wcześniejszego zgłoszenia były niższe od pomiaru; wiąże pomiar powtórzony wyżej.

**Konflikt, którego ta decyzja nie zamyka — patrz P11.** Ramki niosą **dwa rozmiary tekstu
roboczego**, a jeden z nich jest poniżej progu:

Zliczenie wszystkich deklaracji `font-size: Npx` w 41 plikach `makiety/*.dc.html`
(deklaracje w kodzie ramki, nie wyrenderowane teksty), odczyt 2026-08-29:

```
  13 px : 804
  15 px : 869
  17 px : 12
  20 px : 77
  24 px : 8
  26 px : 17
  32 px : 2
  56 px : 34
  64 px : 2
suma deklaracji: 1825
deklaracji ponizej 11 pt (< 14,67 px): 804
```

**804 deklaracje z 1825 (44%) to 13 px = 9,75 pt — poniżej progu ≥ 11 pt.** Podniesienie
podstawy do 15 px **nie usuwa** tych 804 miejsc, bo każde z nich niesie własny rozmiar wpisany
przy elemencie. Wynika z tego, że dwie reguły tego dokumentu **nie mogą być spełnione naraz**:
*„odwzorowanie co do piksela"* (10.1) i *„minimalny rozmiar tekstu ≥ 11 pt"* (12.2) wszędzie tam,
gdzie ramka niesie 13 px. **Nie rozstrzygam tego sam — to decyzja o tym, co widzi użytkownik.**
Pytanie **P11** w rozdziale 16.1.

---

## 11. Doradca

### 11.1 Pięć warstw i jedna linia podziału

| Warstwa | Kto rozstrzyga | Przykład |
|---|---|---|
| 1. Rachunek | **silnik** | „ostrożna linia schodzi pod zero 25 września, brakuje 210,67 zł" |
| 2. Wybór i kolejność rad | **silnik** | „luka płynności bije poduszkę, poduszka bije nadpłatę" |
| 3. Wyzwalacz — czy dziś się odezwać | **silnik** | „zmiana stanu przekracza próg" |
| 4. Sformułowanie | **model językowy** | dobór słów wokół gotowych liczb |
| 5. Decyzja | **człowiek** | nadpłata kredytu, forma opodatkowania |

**Linia biegnie między warstwą 3 a 4** — czyli między **treścią a jej sformułowaniem**, nie między
liczbą a tekstem. Model nie decyduje, **o czym** mówić.

**Wolno modelowi:** dobrać ton i długość zdania; połączyć dwie rady, które silnik podał; odpowiedzieć
na pytanie doprecyzowujące, wołając narzędzie; powiedzieć „nie mam czym tego policzyć".
**Nie wolno:** podać liczby, której nie zwróciło narzędzie; **wymyślić rady, której nie wyprodukował
silnik**; zmienić kolejności rad; ocenić, czy wydatek był sensowny; powiedzieć czegokolwiek
o przepisach poza cytatem z rejestru stawek.

**Dostawca:** Claude przez bramkę AI Vercela. Jeden klucz, możliwość podmiany dostawcy bez zmiany
kodu.

### 11.2 Dwa miejsca

**Karta „Co mam zrobić"** na ekranie Płynności: najwyżej **trzy** działania, każde z kwotą
i z nazwanym kosztem. Karta pokazuje się **także wtedy, gdy wszystko jest w porządku** — wtedy
z jedną pozycją „ile możesz w tym miesiącu odłożyć". Karta znikająca uczy, że jej pojawienie się
oznacza kłopot, a to buduje odruch nieotwierania aplikacji wtedy, gdy jest najbardziej potrzebna.
**Ta karta nie istnieje na dzisiejszej ramce `Main.dc.html` — wymaga projektu przed budową.**

**Ekran Doradca:** rozmowa i dwanaście narzędzi, tak jak na ramce.

### 11.3 Ranking wskaźników — kolejność, w jakiej wchodzą

Szeregowanie: wartość dla użytkownika × wykonalność z dzisiejszych danych.

| # | Wskaźnik | Stan |
|---|---|---|
| 1 | Pierwszy dzień pod kreską + o ile brakuje | policzone, niepokazane |
| 2 | Ile mogę bezpiecznie odłożyć w tym miesiącu | pochodna prognozy, bez nowych danych |
| 3 | Poduszka: ile mam, na ile miesięcy starczy, ile brakuje | wymaga zaznaczenia kategorii niezbędnych |
| 4 | Wolne środki | gotowe |
| 5 | Rezerwa podatkowa (naliczone − zapłacone) | po naprawie kwoty zbiorczej na termin |
| 6 | Przekroczenia planu per kategoria | gotowe; **jedyne uprawnione źródło rad o cięciach** |
| 7 | Który dług nadpłacić i ile zaoszczędzisz | wymaga widzenia pojedynczych kredytów; liczby są: Revolut **416,79 zł** oszczędności, Alior **0,00 zł** |
| 8 | Obciążenie ratą (raty ÷ przychód) | opisowy, rzadko zmienia decyzję |
| 9 | Trend kategorii | **musi mówić „za mało historii"**, nie rysować trendu z dwóch punktów |
| — | **Wartość netto** (−44 773,67 zł) | **celowo poza pierwszym ekranem i poza radami** — liczba prawdziwa, z której nie wynika żadne działanie w tym miesiącu, a która potrafi zniechęcić do otwarcia aplikacji |

### 11.4 Cichy strażnik

Przebieg **raz dziennie**, wynik do `przebiegi_straznika`, widoczny w stopce każdego ekranu.
**Bez powiadomień w v1** (decyzja Darka). Stopka mówi, kiedy ostatnio patrzył i co znalazł.

---

## 12. Bramki odbioru — po czym poznać, że skończone

Zasada: **każda pozycja tej tabeli jest sprawdzeniem, które ma prawo zaświecić się na czerwono.**
Pozycje oznaczone **(P)** to progi proponowane — uzasadnia je mechanizm, nie norma; **nie wolno ich
cytować jako faktu**, dopóki Darek ich nie zatwierdzi.

### 12.1 Poprawność liczb

| Bramka | Jak sprawdzić | Próg |
|---|---|---|
| Zero liczb zmiennoprzecinkowych w ścieżce kwoty | przegląd typów + test na groszach | **zero** |
| Każda stawka pochodzi z rejestru | wyszukanie liczb z ustaw w kodzie silnika | **zero** trafień poza `wiedza/` |
| Migracja danych zachowuje wszystko | liczność i suma kontrolna kwot po obu stronach | **równe** |
| Każdy strażnik ma mutację, która go czerwieni | cytat: co zmieniono, **który test padł po nazwie**, data | **100%** strażników przywołanych jako dowód |
| Historia 2025 nie wchodzi do rachunku podatkowego | test: dodaj wpis `historia-2025`, sprawdź rezerwę | rezerwa **bez zmian** |

### 12.2 Dostępność i percepcja — progi ze standardów, nie propozycje

| Bramka | Próg |
|---|---|
| Kontrast tekstu do tła (osobno dla motywu jasnego i ciemnego) | **≥ 4,5 : 1** tekst zwykły; **≥ 3 : 1** tekst duży |
| Kontrast elementów nietekstowych niosących znaczenie | **≥ 3 : 1** |
| Rozmiar celu klikalnego | **≥ 24 × 24 px**; podwyższony **≥ 44 × 44 px** |
| Minimalny rozmiar tekstu | **≥ 11 pt** — **zostaje w mocy** (D-53); podstawa aplikacji 15 px = 11,25 pt |
| Kolor jako jedyny nośnik informacji | **zero** przypadków — zrzut przepuszczony przez skalę szarości musi pozostać czytelny |

**Uwaga do ostatniej pozycji — znany konflikt.** Zieleń dobrana pod równą wagę z czerwienią ma po
odbarwieniu różnicę **0,00**. Dziś ratuje to znak „+"/„−" przy kwocie. **Znak jest więc wymogiem,
nie ozdobą** — usunięcie go łamie tę bramkę.

**Dziś w projekcie zero strażników kontrastu.** Narzędzie pomiarowe istnieje (`makiety/kontrast.py`),
brakuje bramki w testach. To pierwsza pozycja do dołożenia.

**Uwaga do progu rozmiaru tekstu (v1.3).** Próg **nie został odpuszczony** — plan nocny zapowiadał
inaczej i ta zapowiedź jest sprostowana w rozdziale 10.4. Aplikacja spełnia go podstawą 15 px.
**Ramki go nie spełniają w 804 z 1825 deklaracji rozmiaru** (13 px = 9,75 pt), więc bramka
odwzorowania z 12.7 i ta bramka stoją wobec siebie w sprzeczności wszędzie tam, gdzie ramka niesie
13 px. Rozstrzygnięcie należy do Darka — pytanie **P11** w 16.1. **Do czasu odpowiedzi tej pary
bramek nie wolno cytować jako spełnialnej naraz.**

### 12.3 Układ i hierarchia

| Bramka | Jak sprawdzić | Próg |
|---|---|---|
| Hierarchia istnieje | stosunek wielkości najważniejszej liczby do drugiej | **≥ 1,5 ×** |
| Test mrużenia oczu | rozmyj zrzut, wypisz 3 elementy, które się wybijają; porównaj z listą tych, które **miały** | **3 na 3** |
| Podział na obszary | zasłoń treść, zostaw bloki — czy da się nazwać każdy? | każdy obszar nazwany **jednym słowem** |
| Brak krzyku | policz elementy walczące o uwagę (ramka + kolor + ikona naraz) | **≤ 1** na ekran |
| Grupowanie | odstęp między grupami wobec największego odstępu wewnątrz grupy | **≥ 2 ×** **(P)** |
| Ramki w pierwszym widoku | policz na zrzucie | **≤ 5**, każda powyżej z uzasadnieniem „światło nie wystarczyło" **(P)** |
| Równorzędne wezwania do działania w jednym obszarze | policz przyciski o jednakowej wadze | **1 główne** **(P)** |
| Rozmiary kroju pisma | policz w arkuszu stylów | **≤ 4** **(P)** |
| Jedno pytanie na ekran | czy odpowiedź na pytanie wiodące widać **bez przewijania** | **tak** |
| Głębokość do odpowiedzi wiodącej | policz poziomy od ekranu startowego | **≤ 1** **(P)** |

### 12.4 Tekst

| Bramka | Próg |
|---|---|
| **Instrukcje odeszły** — zdania tłumaczące, jak coś działa | **zero** |
| Prawo trzecie — cięcie słów w pierwszym przejściu | **−50%** |
| Elementy klikalne, przy których trzeba zgadywać, czy są klikalne | **zero** |
| Żargon nieobjaśniony | **zero** |
| **Etykieta opisuje liczbę, którą pokazuje** | **100%** kafelków i nagłówków kolumn |
| Stan wyjątkowy podaje wielkość, nie samo słowo | **100%** — „przekroczony **o 859,49 zł**", nie „przekroczony" |

### 12.5 Zaufanie do liczby

| Bramka | Próg |
|---|---|
| Możliwość obejrzenia rachunku | **100%** liczb wyliczanych ma dostępny rozkład na składniki — w warstwie drugiej, nie pierwszej |
| Znacznik aktualności | **100%** liczb zależnych od stawek i terminów ma widoczny stan aktualności |
| Odniesienie dla liczby ocenianej | **100%** liczb z werdyktem „dobrze/źle" ma cel, przeszłość albo próg |

### 12.6 Zachowanie — testy na żywym człowieku

Jesteś jedynym użytkownikiem, więc jesteś też całą grupą badawczą. **Test pięciosekundowy jest
najważniejszy i wykonalny natychmiast.**

| Bramka | Jak | Próg |
|---|---|---|
| **Test pięciu sekund** | pokaż ekran na 5 s, zabierz, zapytaj: „ile masz pieniędzy i co Cię czeka" | odpowiedź poprawna **bez wahania** |
| Trafność pierwszego kliknięcia | zadanie „dowiedz się, ile możesz wydać" — gdzie pada pierwsze kliknięcie | poprawne dla **wszystkich** zadań wiodących |
| Czas odpowiedzi systemu | od kliknięcia do zmiany na ekranie | **≤ 0,1 s** natychmiastowość; **≤ 1 s** bez wskaźnika postępu |

### 12.7 Odwzorowanie makiety

| Bramka | Próg |
|---|---|
| Zrzut zbudowanego ekranu wobec ramki, ta sama szerokość | porównanie maszynowe **przechodzi** |
| Funkcje z ramki obecne w aplikacji | **100%** pozycji inwentarza z rozdz. 10.2 |
| Odstępstwo od ramki | **zero** bez wpisu w tym dokumencie i zgody Darka |

### 12.8 Awaria do stanu użytecznego

| Bramka | Jak sprawdzić | Próg |
|---|---|---|
| **Doradca bez prądu** | odetnij klucz modelu, porównaj komplet rad i kwot z przebiegiem z modelem | **żadna rada nie znika, żadna kwota się nie zmienia**; wolno zmienić się wyłącznie brzmieniu zdań |
| Rejestr stawek bez API | wyłącz sieć | aplikacja liczy z zatwierdzonych stawek i **mówi, kiedy ostatnio sprawdzała** |
| Brak danych | pusty miesiąc | **stan pusty z wejściem do działania**, nigdy dane przykładowe ani zero udające wynik |

---

## 13. Ryzyka

| # | Ryzyko | Dlaczego realne | Co robimy |
|---|---|---|---|
| R1 | **Zakres v1 to cała aplikacja** | poprzednie podejście z tym samym zakresem dało dziesięć zaprojektowanych ekranów i zero miejsc do wpisania wydatku | wydawanie plasterkami z nazwanym pierwszym momentem użyteczności; `docs/plan-wydawania.md` |
| R2 | **Ręczne wpisywanie zamiera** | zmierzone: arkusz stanął 4 XII 2025, **266 dni ciszy** | trzy dotknięcia do zapisu; podgląd „co ruszy ten wpis"; próg powrotu do tematu importu wypisany w 4.2 |
| R3 | **Strażnik-atrapa** | w poprzednim projekcie **sześć razy** mutacja z planu nie zaczerwieniła wskazanego testu | wymóg czerwieni **po nazwie testu**, nie po „N failed" |
| R4 | **Odwzorowanie makiety zamienia się w „wygląda podobnie"** | raport odbioru u poprzednika ogłosił zgodność „co do piksela", a kontrola obejmowała **wyłącznie pasek nawigacji** | bramka maszynowa; raport odbioru cytuje **zakres kontroli**, nie samą ocenę |
| R5 | **Stawka cicho się starzeje** | ZUS nie ma API; zmiana bywa obwieszczeniem bez nowego aktu | trzy zasilacze, w tym kontrola GUS wykrywająca rozjazd rzędu wielkości |
| R6 | **Czujka aktów zmyśla** | zmierzone w równoległej wersji: przy awarii API zwracała akty nieodróżnialne od prawdziwych | automat **proponuje**, człowiek zatwierdza; brak odpowiedzi to „nie sprawdziłem", nie „nic nie ma" |
| R7 | **Dane finansowe w chmurze** | dwóch dostawców widzi kwoty | dostawcy w UE, szyfrowanie w spoczynku i w tranzycie, eksport wszystkiego na dysk jednym kliknięciem, kopia dobowa |
| R8 | **Model językowy dokłada radę, której nie było** | kontrola pokrycia kwot łapie **kwotę** zmyśloną, a nie **radę** zmyśloną — „ogranicz wydatki" bez liczby przechodzi ją czysto | bramka „doradca bez prądu" (12.8) |

---

## 14. Kolejność wydawania

**Tego rozdziału tu nie ma — i to jest reguła, nie przeoczenie.** Kolejność prac niesie wyłącznie
`docs/plan-wydawania.md` v1.0 (powstał 2026-08-29). Ten dokument go **woła**: sześć plasterków,
z których **plasterek 1 jest pierwszym momentem użyteczności** — wpisujesz wydatek i widzisz,
czy dasz radę do końca okresu.

Jedno ustalenie zostaje tutaj, bo jest wymaganiem, nie kolejnością: **pierwszy moment użyteczności**
to stan, w którym Darek może **wpisać wydatek i zobaczyć, czy dam radę do końca okresu**. Wszystko
przed nim jest przygotowaniem, wszystko po nim jest rozszerzeniem.

---

## 15. Co przestanie działać

Pozycja obowiązkowa (konstytucja firmy §8). Wypisane **przed** wykonaniem, nie po.

| Decyzja | Co przez nią przestaje działać |
|---|---|
| Nowy projekt zamiast rozwijania AI CFO | dostęp do 1019 testów w miejscu, gdzie stoją dziś; przenoszone są razem z kodem, ale **do momentu przeniesienia nie chronią niczego w nowym repozytorium** |
| Chmura zamiast pliku na dysku | zdanie „dane wyłącznie na tym komputerze" przestaje być prawdą; **działanie bez internetu znika całkowicie** |
| PostgreSQL zamiast SQLite | kopia bazy przez skopiowanie jednego pliku; zastępuje ją eksport i kopia po stronie dostawcy |
| Telefon poza v1 | wpisanie wydatku w sklepie — **dokładnie ten moment, w którym wydatek powstaje**. To jest najcięższy skutek tej decyzji i on stoi za ryzykiem R2 |
| Brak powiadomień w v1 | wykrycie luki płynności, gdy Darek nie otworzy aplikacji przez tydzień. Strażnik ją znajdzie, ale **nikt się o tym nie dowie** |
| Automat nie wpisuje stawek | stawka zmieniona ustawą **nie wejdzie sama** — do czasu zatwierdzenia aplikacja liczy starą, mówiąc o tym w chorągiewce |
| Wygaszenie AI CFO | wszystkie ekrany, których Darek używa dziś, przestaną być rozwijane. Do czasu odbioru pierwszego plasterka **stara aplikacja zostaje uruchamialna** — nie kasujemy jej |

---

## 16. Decyzje zamknięte tym dokumentem

Numeracja kontynuuje D-1…D-36 z przekazania poprzednika.

| # | Decyzja | Kiedy |
|---|---|---|
| D-37 | **Nowy projekt, silnik przeniesiony.** AI CFO wygaszany; jego dokumenty zostają nośnikiem wiedzy | 2026-08-28 |
| D-38 | **Jeden użytkownik, aplikacja w chmurze**, dostępna z przeglądarki także spoza domu | 2026-08-28 |
| D-39 | **Telefon poza v1.** Projekt na 1440 px; ramki na 390 px to osobny etap. Próg: po odbiorze v1 | 2026-08-28 |
| D-40 | **Wpisy ręczne, trzy dotknięcia.** Import wyciągu poza zakresem, z progiem powrotu | 2026-08-28 |
| D-41 | **v1 = pełny zakres, jedenaście tras**, wydawany plasterkami | 2026-08-28 |
| D-42 | **Doradca: karta „Co mam zrobić" + czat. Bez powiadomień w v1.** Zamyka P4 i P5 | 2026-08-28 |
| D-43 | **Próg poduszki = 6 × wydatki niezbędne**; klasyfikacja kategorii jako pole w Ustawieniach. Zamyka P1, częściowo P10 | 2026-08-28 |
| D-44 | **Hosting: Vercel + PostgreSQL w Neonie** | 2026-08-28 |
| D-45 | **Model językowy: Claude przez bramkę AI Vercela** | 2026-08-28 |
| D-46 | **204 wpisy z 2025 wchodzą jako oznaczona historia** — widoczne w Raportach, poza rachunkiem | 2026-08-28 |
| D-47 | **Nazwa aplikacji: Doradca Finansowy** | 2026-08-28 |
| D-48 | **Baza wiedzy = rejestr stawek w bazie; automat proponuje, człowiek zatwierdza** | 2026-08-28 |
| D-49 | **Makieta jest wiążąca w dwóch wymiarach: zakresu i wyglądu** | 2026-08-28 |
| D-50 | **S-1: przy sprzeczności o VAT rację ma ramka Doradcy** (memoriałowo, termin 25 XI); `Firma.dc.html` do poprawki | 2026-08-28 |
| D-51 | **S-2: próg poduszki jest liczony**, ręczne nadpisanie widoczne jako odstępstwo | 2026-08-28 |
| D-52 | **S-3: sekcja „gdzie leżą dane" w Ustawieniach do przeprojektowania** pod chmurę | 2026-08-28 |
| D-53 | **Typografia: krój z ramki, rozmiar 15 px.** Krój bezszeryfowy dokładnie jak w ramkach; podstawa **15 px** zamiast 13 px z ramki; bramka „≥ 11 pt" **zostaje w mocy**, bo 15 px = 11,25 pt | 2026-08-29 |
| D-54 | **Karta „Co mam zrobić" wchodzi do v1** — na ekranie Płynność, jako komponent podrzędny wobec wiersza zamknięcia. Najwyżej trzy działania, każde z **kwotą** i **nazwanym kosztem**; karta jest widoczna **zawsze**, także w miesiącu bez deficytu | 2026-08-29 |
| D-55 | **Linia „Ile mogę jeszcze rozdysponować…" NIE wraca na ekran Płynność.** D-16 (Darek, 28.08 16:50) uchyliła D-10 (Sophia, 28.08 01:19); miejscem docelowym jest ekran **Budżet**, jak wskazała D-16 | 2026-08-29 |
| D-56 | **Zakres karty w v1 to wyłącznie C1** („ile mogę odłożyć w tym miesiącu"). C2 (nadpłata kredytu) poza zakresem do czasu, aż zobowiązania poniosą oprocentowanie; C3 nie wchodzi do karty; C4 poza v1 (D-42). **Niewykorzystane miejsca zostają puste** | 2026-08-29 |
| D-57 | **Znak słowny w nagłówku brzmi `FINANSE`** — dopuszczalne wykonanie D-47, nie odstępstwo od niego: D-47 nazywa aplikację, nie napis w pasku. Pełna nazwa stoi w tytule okna | 2026-08-29 |
| D-58 | **Minus typograficzny (U+2212) jest wiążący dla każdej kwoty ujemnej** na ekranie; jedynym nośnikiem formatowania kwot zostaje `silnik/prezentacja.py`, a widok go **woła** | 2026-08-29 |
| D-59 | **Sekcja „Gdzie leżą dane" pokazuje ODCZYT, nie obietnicę** — dostawca, region, kraj i data odczytu pochodzą z konfiguracji połączenia. Dopóki region nie jest znany, ekran mówi to wprost | 2026-08-29 |

**D-53 — koszt nazwany.** 15 px zamiast 13 px **przesuwa wysokości bloków tekstu**, więc ramka
i ekran **nie zejdą się dokładnie w pionie**. Bramka odwzorowania (12.7, próg ≤ 2% różniących się
pikseli) mierzy to jako różnicę **rozproszoną po tekstach, nie jako przesunięcie układu**. Jeśli
progu nie przejdzie, **wolno podnieść próg do 4% wyłącznie dla różnic tekstowych** — **nigdy dla
położenia elementów**. Podniesienie progu dla położenia byłoby zdjęciem bramki, nie jej strojeniem.

**Czego D-53 nie rozstrzyga:** 804 deklaracji 13 px w samych ramkach (rozdział 10.4) oraz kroju
szeryfowego na kwotach, obecnego w 37 z 41 ramek i nieobecnego dziś w `powloka.css`. Pierwsze —
pytanie P11; drugie — do przeniesienia w zadaniu Z1, bez osobnej decyzji.

**D-54 — czego karta nie robi i jak zmierzono pierwszeństwo.** Karta nie powtarza werdyktu
z wiersza „Najniżej" — nazywa **działanie**, nie fakt. Pierwszeństwo wiersza zamknięcia zmierzone
na `makiety/Main.dc.html`: wiersz zamknięcia **56 px**, największy stopień pisma wewnątrz karty
po D-55 **15 px**, stosunek **3,73×** wobec progu Kruga ≥ 1,5×. Ramka wiążąca dla ekranu:
`makiety/Main.dc.html`; ramka opisująca **oba stany karty** (jest co robić / wszystko w porządku):
`makiety/CoMamZrobic.dc.html`.

**Powód, dla którego karta nie znika w dobrym miesiącu.** Karta znikająca uczy, że jej pojawienie
się oznacza kłopot, a to buduje odruch **nieotwierania aplikacji wtedy, gdy jest najbardziej
potrzebna**. W miesiącu bez deficytu karta niesie **jedną** pozycję — „ile możesz w tym miesiącu
odłożyć" — i nie dorabia drugiego działania na siłę.

**D-54 (ciąg dalszy) — karta należy do WSZYSTKICH stanów ekranu pierwszego, nie tylko do złego.** To jest
warunek, dla którego kartę w ogóle zamawialiśmy, i dziś **nie jest spełniony na ramkach**.
Zmierzone 2026-08-29, `grep -c "Co mam zrobić"` na wariantach ekranu pierwszego:

| Ramka | Co przedstawia | Karta |
|---|---|---|
| `Main.dc.html` | stan zły (schodzisz poniżej zera) | **1** |
| `Main-Ciemny.dc.html` | to samo, motyw ciemny | **1** |
| `Main-Dobrze.dc.html` | stan dobry — w nośniku projektowym opisany jako **„stan NAJCZĘSTSZY"** | **0** |
| `NieWiem.dc.html` | stan „prognoza nie wie" — **stan startowy**, czyli pierwszy, jaki Darek zobaczy | **0** |

Ramka jest wiążącą specyfikacją zakresu (D-49), więc ramka stanu dobrego **bez karty znaczy
„tu karty nie ma"** — czyli dokładnie kartę znikającą, przed którą to zlecenie miało chronić.
Stan 2 opisany na `CoMamZrobic.dc.html` **nie zastępuje** ramki ekranu: to arkusz specyfikacji,
poza bramką `--kontrola` (rozdział 17, pozycja 13). **Wymagane: karta wchodzi na
`Main-Dobrze` i na `NieWiem`.** W stanie „nie wiem" karta nie znika i nie zgaduje — mówi, czego
brakuje, żeby dało się cokolwiek policzyć (§3.7 konstytucji projektu).

**Ile działań w v1 — pytanie zamknięte, żeby nikt go nie zgadywał.** Górna granica to trzy, ale
z D-56 wynika, że w v1 działanie jest **dokładnie jedno**. Wykonawca **nie projektuje** układu
dla dwóch ani trzech pozycji i nie dorabia treści do pustych miejsc.

**D-55 — sprostowanie jawne, bo przesłanka pochodziła z nośnika wtórnego.**
`../AI CFO/docs/makiety-v2/decyzje-projektowe.md` niesie w wierszu 619 zdanie, dosłownie:
*„Zostaje na ekranie **decyzją Sophii z 2026-08-28**, ale traci pierwszeństwo: 20 px wobec 56 px."*
**To zdanie jest dziś nieprawdziwe.** Nośnikiem pierwotnym decyzji jest
`../AI CFO/docs/2026-08-28-przekazanie-do-implementacji.md` v1.9 (status: *jedyny nośnik decyzji*),
gdzie **D-10 stoi przekreślona**, z adnotacją *„UCHYLONA przez D-16 (28.08, 16:50)"*.
D-16 brzmi: *„Wolne środki ZNIKAJĄ z ekranu płynności. Darek, 16:50: »Zdejmij liczbę z dołu,
prognoza wystarczy«"* — z rachunkiem, który Darek złożył sam: `9 920,79 + (−10 131,46) = −210,67`,
**co do grosza werdykt prognozy stojący wyżej na tym samym ekranie**. Rachunek powtórzony na
dzisiejszej ramce zgadza się: `3 025,33 − 660,00 − 2 576,00 = −210,67`.
Liczba niesie więc treść już obecną, tylko w postaci nieczytelnej bez dodawania w pamięci —
i dodatkowo ma **znaną, nierozstrzygniętą wadę czytelności** (§4.4 tamtego dokumentu:
*„czyta się jak katastrofa, a znaczy »nie zaplanowałeś przychodu we wrześniu«"*, pytanie 3 nadal
otwarte). Zmiana miejsca z dołu ekranu do wnętrza karty tej wady nie usuwa.

**D-57 — pomiar, na którym stoi.** Budżet wiersza nagłówka przy ramce 1440 px i wcięciu 40 px
wynosi **1360 px**. Wiersz niesie: znak słowny, przycisk księgowania, dziewięć pozycji paska
i wskaźnik daty. Pomiar `makiety/miara.py` powtórzony 2026-08-29, z **doliczonym wskaźnikiem daty**
(171,2 px), którego samo narzędzie nie liczy:

| Znak słowny | Szerokość wiersza | Zapas do 1360 px | Werdykt |
|---|---|---|---|
| `FINANSE` (światło 0,12 em) | 1314,6 px | **45,4 px** | mieści się |
| `Doradca` (0,12 em) | 1325,5 px | 34,5 px | mieści się, ale **koliduje** z pozycją paska „Doradca" — to samo słowo w tym samym wierszu znaczyłoby dwie rzeczy |
| `Doradca Finansowy` (0,16 em) | 1449,4 px | **−89,4 px** | **nie mieści się** |
| `Doradca Finansowy` (0,12 em) | 1439,2 px | −79,2 px | **nie mieści się** |

Pełna nazwa mieści się **wyłącznie** po skróceniu wskaźnika daty do `6 X · 09:40` (zapas 13,9 px),
czyli **kosztem roku** — w aplikacji, której cała treść to zobowiązania przypisane do lat.
Ta zamiana jest odrzucona.
**Jedna wartość wiążąca dla wykonawcy:** `interfejs/lib/ekrany.ts`, stała `ZNAK_SLOWNY`, wartość
`"FINANSE"`, światło 0,12 em. Dziś stoi tam `"Doradca"` — **to jest rozjazd do naprawy w kodzie,
nie w ramkach.** Pełna nazwa „Doradca Finansowy" zostaje w tytule okna
(`interfejs/app/layout.tsx`), więc D-47 ma pokrycie w miejscu, w którym system operacyjny
pokazuje nazwę aplikacji.

**D-58 — dziś trzy nośniki znaku minus, a wyznaczony mówi co innego niż ekran.**
Pomiar 2026-08-29: `rdzen/prezentacja.zloty(Decimal("-210.67"))` zwraca `'-210,67\xa0zł'`
— **dywiz ASCII, bez U+2212**; `interfejs/lib/kwota.ts` składa własny prefiks `−` (U+2212);
ramki po Z3 niosą U+2212. Rozstrzygnięcie idzie **za ramką** (D-49): na ekranie ma stać minus
typograficzny. Wykonanie należy do Z4 — `prezentacja.py` zmienia znak, a widok przestaje
formatować kwoty samodzielnie.

**D-59 — czego dzisiejsze brzmienie nie spełnia.** Ramka `Ustawienia.dc.html` niesie zdanie:
*„Baza leży u Neona (PostgreSQL), serwery w Unii Europejskiej — dokładny region potwierdzamy przy
zakładaniu projektu."* Trzy zastrzeżenia. **Po pierwsze**, „potwierdzamy przy zakładaniu projektu"
jest notatką wykonawcy do wykonawcy; użytkownik pytający „gdzie leżą moje pieniądze na papierze"
dostaje w odpowiedzi cudzy plan pracy. **Po drugie**, położenie danych jest **stanem faktycznym
działającego systemu**, więc musi być **odczytane**, nie wpisane w ekran; zdanie wpisane na stałe
będzie prawdziwe najwyżej przez przypadek. Pomiar 2026-08-29: w `Doradca Finansowy/.env` jest
**zero wystąpień słowa `neon`**, a baza stoi dziś w kontenerze na porcie 5434 — na dziś **oba
człony zdania są nieprawdziwe**. **Po trzecie**, ten sam fakt stoi w dwóch miejscach ekranu
(nagłówek sekcji Ustawienia: *„24 kategorie · dane w chmurze (Unia Europejska)"*) — dwa nośniki
jednej reguły. Wymagania: jeden nośnik; treść z odczytu konfiguracji (dostawca, region, kraj,
data odczytu); dopóki region nie jest znany, ekran mówi to **wprost i po ludzku**, razem z tym,
co się z tym robi — dokładnie jak każdy inny stan „nie wiem" (§3.7 konstytucji projektu).
Umieszczenie bazy w Unii Europejskiej **zostaje wymaganiem wiążącym** (D-38, D-44) — ale jest
wymaganiem do spełnienia, nie zdaniem do pokazania, zanim będzie prawdziwe.

### 16.1 Pytania nadal otwarte — nie zgaduj ich

| # | Pytanie | Co blokuje |
|---|---|---|
| P6 | Czy lista kategorii nietykalnych (`Monika i Ada`, `Zdrowie`, `Czesne`, `Podatki i ZUS`) jest kompletna? Czy `Transport` do niej należy? | rady o cięciach |
| P7 | Czy „miejsce na kompetencje" ma być historią stawki godzinowej z polem „powód"? Czy jest kompetencja, która **nie zmienia stawki**? | kształt ekranu Godziny |
| P8 | Ile pul oszczędnościowych na start i czy pula awaryjna ma pierwszeństwo przed dopełnieniem poduszki? | model celów |
| P9 | Czy poduszka ma termin? Dziś w aplikacji stoi 2027-12-31, a definicja („cały czas rosnąć") terminu nie zawiera | tempo wymagane |
| P10a | Czy `Transport`, `Monika i Ada` i część `Zakupy` są niezbędne? | dokładność progu poduszki |
| P10b | **Czy przy utracie zlecenia zawieszasz działalność?** Jeśli tak, ZUS znika z niezbędnych i próg spada o **11 560,56 zł** — największa pojedyncza pozycja w tym rachunku | j.w. |
| P11 | **Ramka kontra próg czytelności: która wygrywa przy 13 px?** Ramki niosą **804 deklaracje 13 px = 9,75 pt** (44% wszystkich), a bramka 12.2 żąda ≥ 11 pt. Trzy wyjścia: (a) odwzorowujemy ramkę i **zawieszamy próg dla tekstów drobnych**, nazywając to jawnie; (b) podnosimy 13 px do 15 px także w tekstach drobnych i **przyjmujemy trwałą różnicę wobec ramki**; (c) **poprawiamy ramki** i dopiero z nich odwzorowujemy | odbiór **każdego** ekranu — dziś bramki 12.2 i 12.7 nie mogą przejść jednocześnie |

---

## 17. Pozycje niezweryfikowane

Etykieta jest dopuszczalna; udawanie sprawdzonego nie jest.

1. **Wszystkie progi oznaczone (P) w rozdziale 12** — propozycje z fundamentu projektowego,
   niezatwierdzone przez Darka. Nie wolno ich cytować jako ustaleń.
2. **Limit odliczenia składki zdrowotnej (14 100 zł)** — podatki.gov.pl przypisuje go do 2026,
   biznes.gov.pl do 2025. Dotyczy wyłącznie podatku liniowego, więc **nie wpływa na dzisiejsze
   kwoty Darka**; wchodzi do rejestru z wypełnionym polem `niezweryfikowane`.
3. ~~**Liczba tras (~26)** — oszacowanie z inwentarza funkcji.~~ **ZMIERZONE 2026-08-29.**
   Pozycja zamknięta, ale **rozdzielona na dwie liczby, bo mieszały się dwie różne rzeczy**
   (sprostowanie S1, rozdział 9): **poprzednia aplikacja ma 24 działające trasy** (22 odczytu,
   2 zapisu — pomiar na obiekcie routera), a **nowa aplikacja ma spis 36 pozycji do zbudowania**
   (15 odczytu, 21 zapisu, `api/trasy.py`). Wcześniejsze „10" i „26" są obalone.
4. **Wykonalność funkcji Pythona na Vercelu dla tego silnika** — platforma obsługuje Python
   natywnie, ale **nie zmierzyłem** czasu zimnego startu ani rozmiaru paczki dla tych zależności.
   Do sprawdzenia w pierwszym plasterku, przed budową ekranów.
5. **Koszt miesięczny hostingu** — zakładam mieszczenie się w progach darmowych; **nie policzone**.
6. **Zachowanie czujki ELI przy zmianie kształtu odpowiedzi API** — sprawdzone raz, 2026-08-28.
   Pomiar konfiguracji ma termin ważności.
7. **Że 204 wpisy z 2025 dadzą sensowny raport** — dwa pełne miesiące to za mało na trend
   i wskaźnik ma o tym **mówić wprost**, zamiast rysować linię z dwóch punktów.
8. **Bramka „każda stawka pochodzi z rejestru" (12.1) nie ma dziś strażnika** — jest listą
   kontrolną, nie testem. Wiadomo natomiast, że **zaczerwieniłaby się na pięciu miejscach**
   z rozdziału 8.4. Etykieta jawna: **niepotwierdzona testem**, nie „spełniona".
9. **Czy 15 px zmieści się w progu 2% różniących się pikseli** wobec ramki na 13 px —
   **nie zmierzone**, bo żaden ekran nie jest jeszcze zbudowany. Pierwszy pomiar w zadaniu Z1;
   dopiero on rozstrzygnie, czy zapas z D-53 (podniesienie progu do 4% dla różnic tekstowych)
   jest w ogóle potrzebny.
10. **Że próg ≥ 11 pt i odwzorowanie co do piksela dadzą się spełnić naraz** — **pomiar mówi, że
    nie** (804 deklaracje 13 px w ramkach, rozdział 10.4). Pozycja czeka na odpowiedź **P11**;
    do tego czasu **nie wolno cytować obu bramek jako spełnialnych jednocześnie**.
11. **Region serwera bazy — nieustalony i niezmierzony.** Pomiar 2026-08-29: `grep -c neon
    "Doradca Finansowy/.env"` zwraca **0**; projektu u dostawcy nie ma, baza stoi w kontenerze
    na porcie 5434. Zdania „serwery w Unii Europejskiej" **nie wolno dziś cytować jako faktu**
    ani pokazywać użytkownikowi (D-59). Luka zamyka się w chwili założenia projektu, odczytem
    regionu z konfiguracji.
12. **`makiety/miara.py` mierzy mniej, niż drukuje.** Narzędzie sumuje znak słowny, przycisk
    księgowania i pozycje paska, ale **nie liczy wskaźnika daty**, który `buduj-makiety.py`
    wstawia w ten sam wiersz nagłówka (`UZYTKOWE = ()`, wiersz 125). Zmierzone 2026-08-29:
    narzędzie drukuje *„ZAPAS w jednej linii 200,6 px"*, a sam wskaźnik daty ma **171,2 px** —
    realny zapas to **45,4 px**. Kto zaufa wydrukowi, wyciągnie wniosek odwrotny do prawdziwego
    (narzędzie orzeka „Doradca Finansowy MIESCI SIE", a nazwa **nie mieści się**). Werdykt D-57
    stoi na pomiarze z **doliczoną** datą, nie na wydruku narzędzia. **Narzędzie do naprawy** —
    wraca do Mili.
13. **Karta „Co mam zrobić" istnieje w dwóch plikach, a bramka pilnuje jednego.** Treść karty
    stoi równolegle w `makiety/Main-zrodlo.dc.html` (ekran) i `makiety/CoMamZrobic.dc.html`
    (specyfikacja dwóch stanów). Zmierzone 2026-08-29: `buduj-makiety.py --kontrola` sprawdza
    **21 plików** i `CoMamZrobic.dc.html` **nie jest wśród nich** — rozjazd obu kopii nie zapali
    się na niczym. Świadomy drugi nośnik, dopuszczalny wyłącznie z progiem: **przy pierwszej
    zmianie treści karty** obie kopie schodzą do jednej albo dostają strażnika.

---

## 18. Przegląd samokrytyczny

Pięć słabości tego dokumentu, wypisanych przez autora:

1. **Zakres v1 jest za duży i wiem o tym.** Darek wybrał wszystko; zapisałem to jako wymaganie
   i obudowałem plasterkami, ale ryzyko R1 zostaje realne i nie zniknie od tego, że je nazwałem.
2. **Karta „Co mam zrobić" nie ma ramki.** Jest sercem produktu nazwanego „Doradca Finansowy",
   a jedyny ekran, na którym ma stać, jej nie przewiduje. To jest luka projektowa do zamknięcia
   **przed** budową Płynności, nie po.
3. **Nie zmierzyłem Vercela z tym silnikiem.** Cała architektura stoi na założeniu, że Python
   z tymi zależnościami zmieści się w funkcji. Pozycja 4 rozdziału 17.
4. **Kryteria z rozdziału 12 są liczne i część z nich nikt nie sprawdzi ręcznie.** Te, które nie
   mają automatu, zestarzeją się w milczeniu. Do rozstrzygnięcia w planie: które z nich stają się
   testem, a które zostają listą kontrolną przy oddaniu ekranu.
5. **Sześć pytań z 16.1 zostaje otwartych**, a dwa z nich (P10a, P10b) wpływają na kwotę, którą
   aplikacja pokaże jako próg poduszki. Do czasu odpowiedzi próg jest **przedziałem**, i aplikacja
   ma to mówić, a nie pokazywać środek przedziału jako liczbę.

### 18.1 Przegląd samokrytyczny zmian v1.3 (Ethan)

1. **Pierwsza wersja tego rozdziału twierdziła, że kopie z 8.4 niosą „tę samą tabelę".**
   Porównałem wtedy **wartości**, a nie zachowanie na granicach przedziałów, i napisałem to jako
   hipotezę do sprawdzenia w Z4. Sprawdziłem przed oddaniem — **kopie się rozjeżdżają na progu
   300 000 zł**, o 7 973,52 zł rocznie. Wniosek dla następnego czytelnika: „ta sama tabela" na oko
   znaczy „nie porównałem granic".
2. **Nie napisałem strażnika dla żadnej z sprostowanych rzeczy.** Trzy sprostowania to trzy
   twierdzenia, które za miesiąc znów się zestarzeją — dokładnie jak „10 tras" zestarzało się
   w jednym commicie. Jedyna obrona, jaką zostawiam, to komendy wpisane w dokument, żeby dały się
   powtórzyć. To słabsze niż test.
3. **Liczba 24 opisuje trasy zarejestrowane, nie trasy działające.** Zbudowałem obiekt routera
   i policzyłem jego zawartość; **nie wysłałem ani jednego zapytania**. Trasa, która zwraca błąd,
   liczy się w tym pomiarze tak samo jak trasa sprawna.
4. **P11 to konflikt, który znalazłem, i którego nie zamknąłem.** Zostawiam go Darkowi zamiast
   rozstrzygnąć — bo dotyczy tego, co widzi użytkownik. Koszt jest realny: **każdy ekran oddany
   przed odpowiedzią trafia w bramkę, której nie da się przejść w całości.**
5. **Nie ruszyłem dwóch sprzeczności, które widziałem po drodze.** Rozdział 7.4 nadal mówi
   *„żaden z trzech zasilaczy"*, a ryzyko R5 nadal wymienia *„kontrolę GUS"* — mimo że v1.2 zdjęła
   GUS i zasilacze są dwa. To resztki po poprzedniej wersji, nie moje zmiany; zgłaszam je zamiast
   poprawić po cichu poza zakresem zlecenia.
