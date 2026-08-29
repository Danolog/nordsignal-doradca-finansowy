# Spis wiążący — ekran Budżet (W9)

**Wersja:** v1.0 · 2026-08-29 · autor: Mila (Product Designer) · zlecenie: Oliver (COO), plan `docs/plan-chmura-2026-08-29.md` §W9.

**Status: do budowy.** Ten dokument jest specyfikacją dla **Maxa** (trasy) i **Jacka** (ekran) —
nie relacją z pracy. Woła `api/trasy.py`, `makiety/ekrany.py`, `docs/PRD.md`, `testy/test_nosniki.py`;
nie powtarza ich treści.

**Zrzut ramki (dowód wizualny, 1440×1483 px, pełna strona):** `makiety/zrzuty/Budzet-ramka-dowod-W9.png`.

**Sprostowanie ścieżki (Oliver → Mila, ta sama sesja).** Zlecenie wskazywało `makiety/zrzuty/`
z uzasadnieniem „tam już mieszkają zrzuty ramek" — **pomiar pokazuje, że katalog nie istniał**
(utworzony teraz). Zrzuty ramek z bramki odwzorowania realnie mieszkają w `interfejs/zrzuty/`
(`KATALOG_ZRZUTOW` w `interfejs/narzedzia/porownaj-z-makieta.mjs:78`) — ale **ta ścieżka jest
w `.gitignore` w.11** („wytwory budowania i bramki odwzorowania"), więc plik tam odłożony **nie
przetrwałby commita** i zniknąłby dokładnie tak, jak zlecenie chciało temu zapobiec. Sam kierunek
zlecenia (`makiety/zrzuty/`, nowy katalog) jest więc słuszny mimo błędnego uzasadnienia — i tam
plik faktycznie stoi, potwierdzone `git check-ignore` (brak trafienia, plik śledzony).

---

## 0. Ramka: pomiar, nie deklaracja

```
$ node narzedzia/mierz-budzet.mjs   (playwright, viewport 1440×900, plik lokalny)
{"scrollWidth":1440,"scrollHeight":1483,"bodyScrollWidth":1440,"bodyScrollHeight":1483}
```

Ramka **`makiety/Budzet.dc.html`** (169 linii, 23 408 B) i jej draft **`makiety/Budzet-zrodlo.dc.html`**
istnieją (`ls`). **Szerokość ramki jest stała dla całej aplikacji: 1440 px**
(`makiety/miara.py:44`, `interfejs/narzedzia/porownaj-z-makieta.mjs:67`). **1483 px to WYSOKOŚĆ
dokumentu przy tej szerokości**, zmierzona wyżej i zgodna z `makiety/ekrany.py:81` (pole `wysokosc`).

**Sprostowanie nośnika.** `docs/plan-chmura-2026-08-29.md` w.262 zapisuje „Ramka `Budzet.dc.html`
(1483 px)" bez podpisu wymiaru — czytelne jako szerokość, jest wysokością. Do poprawki przy
najbliższej edycji tego planu.

**Ramka wiążąca do porównania maszynowego jest `Budzet.dc.html` (bez sufiksu)** — to jej nazwę woła
`porownaj-z-makieta.mjs` i `ekrany.py`. `Budzet-zrodlo.dc.html` to draft (inny nagłówek: przełącznik
motywu zamiast pełnego paska dziewięciu pozycji) — nie jest przedmiotem bramki odwzorowania.

---

## 1. Inwentarz funkcji z ramki — z kontrolą liczności

| Element | Liczba | Kontrola |
|---|---|---|
| Kafelki planu (siatka 3 kolumn `1fr 1fr 1fr`) | **3**: Wydatki osobiste z planu (2 614,81 zł) · Rezerwa na podatki (7 696,65 zł) · Plan miesiąca razem (10 311,46 zł) | 2 614,81 + 7 696,65 = 10 311,46 ✓ |
| Wiersz bilansu (poza siatką kafelków — wyjątek Krug §3.2, wygląd inny świadomie) | **1**: „Bilans planu −2 614,81 zł" | zgadza się ze znakiem ujemnym sumy wydatków |
| Selektory w nagłówku karty | **2**: „październik 2026" (w zakresie) i „Wybrany miesiąc" (**poza zakresem** — patrz §7) | — |
| Sekcje nazwane etykietą wielkimi literami | **4**: Plan kontra wykonanie · Cele oszczędnościowe · Historia · Budżet (nagłówek karty) + **1 zdanie narracyjne bez etykiety** („Z planu... nie wydałeś jeszcze nic") | `grep` 15 etykiet 13px uppercase, zwinięte do 4 sekcji + kafelki |
| Pozycje planu razem (licznik z nagłówka „4 pozycje planu") | **4** = 3 wydatki (Kredyty, Czesne, Energia Elektryczna) + 1 cel (Poduszka finansowa) | zgadza się z nagłówkiem „4 pozycje planu · 0 wpisów" |
| Paski postępu | **4** (po jednym na każdą z 4 pozycji wyżej) | `grep -c "position: relative; display: block; height: 14px"` = 4 |
| Tabele wielokolumnowe | **3 wystąpienia**: Plan kontra wykonanie i Cele współdzielą `210px 130px 1fr 130px 190px`; Historia ma własny `110px 130px 1fr 160px 160px` | `grep -n grid-template-columns` |
| Przyciski/linki specyficzne dla ekranu (poza paskiem 9 pozycji i akcją Księgowanie w nagłówku) | **5**: Dodaj pozycję planu · Skopiuj z września · Dodaj cel · Popraw zaznaczony · Usuń zaznaczone | policzone poimiennie, `grep -oE` |
| Stany widoczne na tej ramce | **3**: wypełniony (Wydatki, Cele) · pusty poprawnie złożony (Przychody i oszczędności — `<p>` pełnej szerokości poza siatką) · **pusty źle złożony** (Historia — patrz §6) | porównanie dwóch pustych stanów w tym samym pliku |

Całkowita liczba klikalnych elementów na ramce wiążącej (`Budzet.dc.html`): **15 linków, 0 przycisków**
— 1 akcja Księgowanie + 9 pasek + 5 wymienione wyżej.

---

## 2. Cztery operacje P-1 — nazwane imiennie

Nazwa „P-1" ma nośnik: `../AI CFO/docs/2026-08-28-przekazanie-do-implementacji.md`, §4, w.396–419
(rozstrzygnięcie Darka 2026-08-28, 14:32–14:45).

1. **dodać transakcję** — `zapisz_wpis` → `POST /api/wpisy` (ekran Księgowanie, **zbudowane**)
2. **wycofać transakcję** — `usun_wpis` → `DELETE /api/wpisy/{id}` (Księgowanie, **zbudowane**)
3. **ustawić / zmienić pozycję planu** — `zapisz_plan` → `POST /api/plan` + `PUT /api/plan/{id}` (Budżet)
4. **zakończyć pozycję planu** — `zakoncz_plan` → `POST /api/plan/{id}/zakoncz` (Budżet, **nie** `usun_plan`)

Piąta trasa w `WARUNEK_WYLACZENIA` (`POST /api/plan`) istnieje, bo operacja 3 rozbija się na dwie
trasy HTTP (dodanie vs zmiana) — wprost w asercji `api/trasy.py:109`.

---

## 3. Sześć tras — stan i element ramki

Kontrola liczności: `[t for t in trasy.WSZYSTKIE if t.ekran == 'budzet']` → **dokładnie 6**, zero
brakujących/nadmiarowych.

```
$ python3 -c "from api import trasy_ksiegowanie, trasy_plynnosc; ..."
ZBUDOWANE: ('/api/ksiegowanie', '/api/wpisy', '/api/wpisy/{id}', '/api/wpisy/podglad',
            '/api/plynnosc', '/api/kotwica')
```

| Trasa | Stan | Element ramki |
|---|---|---|
| `GET /api/budzet` | brak | cały ekran (kafelki, bilans, tabele, cele) |
| `POST /api/plan` | brak | „Dodaj pozycję planu" |
| `PUT /api/plan/{id}` | brak | **brak elementu na ramce — rozstrzygnięte w §4** |
| `POST /api/plan/{id}/zakoncz` | brak | **brak elementu na ramce — rozstrzygnięte w §4** |
| `POST /api/plan/kopiuj` | brak | „Skopiuj z września" |
| `POST /api/cele` | brak | „Dodaj cel" |

Żadna z sześciu jeszcze nie istnieje (`ZBUDOWANE` obejmuje dziś wyłącznie Księgowanie i Płynność)
— zgodne z oczekiwaniem, W9 dopiero startuje.

---

## 4. Element dla `PUT /api/plan/{id}` i `POST /api/plan/{id}/zakoncz` — WIĄŻĄCE POLECENIE DLA JACKA

**Odstępstwo nazwane od §3.6 konstytucji projektu**, tego samego rodzaju co W7/W8: ekran ma dwie
trasy, dla których żadna ramka nie rysuje elementu. Zgłoszone jawnie, nie budowane po cichu.
**Próg konsolidacji: ramka Budżetu przy najbliższej edycji dostaje te dwa elementy** (analogicznie
do progu strażnika `test_ZADNA_ramka_NIE_RYSUJE_pola_wpisywania` z W8).

**Zasada nadrzędna, ustalona już w tej sesji:** kontrolka NIE może nazywać się ani działać jak
„usuń"/„skasuj" — historia zostaje (§5). Poniższe reużywa w całości istniejący wzorzec wizualny
ramki (linki `#4A5267`/`#6B6252`, bez ramki/tła, `text-decoration: none`) — nie wprowadza nowego
typu kontrolki.

### 4.1 `PUT /api/plan/{id}` — zmiana istniejącej pozycji

- **Gdzie stoi:** nazwa kategorii w tabeli „Plan kontra wykonanie" (dziś zwykły `<span>`: „Kredyty",
  „Czesne", „Energia Elektryczna") staje się linkiem — ten sam styl co „Popraw zaznaczony" w Historii
  (kolor przygaszony, bez tła, `text-decoration: none`), z `aria-label="Zmień pozycję planu: Kredyty"`
  (wzorzec zapożyczony z `Ustawienia.dc.html`: `aria-label="Zmień nazwę Inwestycje"`).
- **Co robi klik:** otwiera **ten sam panel**, który otwiera „Dodaj pozycję planu" — wypełniony
  bieżącymi wartościami tej pozycji (kategoria, kwota, dni/cykl płatności) i z nagłówkiem panelu
  „Zmień pozycję planu" zamiast „Dodaj pozycję planu". Zapis w tym trybie woła `PUT /api/plan/{id}`,
  nie `POST /api/plan`. **To jest ta sama kontrolka co „Dodaj pozycję planu", z dwoma trybami —
  nie nowy komponent.**
- **Przed / po:** przed — wiersz „Kredyty" jest zwykłym tekstem, nieklikalny. Po — „Kredyty" jest
  linkiem; klik otwiera panel z polami Kategoria/Kwota/Dni wypełnionymi „Kredyty" / „1 624,81 zł" /
  „1 X" (dzień poprawiony w §11.3 — było „1 i 12 X", ramka scalała dwie reguły planu w jedną).

### 4.2 `POST /api/plan/{id}/zakoncz` — zakończenie reguły

- **Gdzie stoi:** wewnątrz panelu z §4.1 (trybu „Zmień pozycję planu"), pod polami formularza,
  osobny mniejszy link — ten sam poziom wizualny co „Usuń zaznaczone" w Historii, ale **inny napis
  i inne działanie**.
- **Napis:** „Zakończ tę pozycję od października 2026" — z NAZWĄ BIEŻĄCEGO MIESIĄCA wpisaną w
  zdanie (nie „Usuń", nie „Skasuj"; §3.5 — etykieta niesie od razu wielkość/zakres skutku, nie samo
  słowo).
- **Co robi klik:** pokazuje potwierdzenie jednym zdaniem: *„Wcześniejsze miesiące zostają bez
  zmian — Kredyty przestanie się pojawiać w planie od października 2026."* + przycisk „Zakończ".
  Wywołuje `POST /api/plan/{id}/zakoncz`. **Nigdy `DELETE`.**
- **Przed / po:** przed — pozycja „Kredyty" widoczna w tabeli za bieżący i przyszłe miesiące. Po
  zakończeniu — „Kredyty" znika z planu **od bieżącego miesiąca w przód**; **przeszłe miesiące
  (wrzesień, gdy istniały) pokazują tę pozycję bez zmian** na Raportach i w historycznym „Plan
  kontra wykonanie" (patrz §5, Z-9).

**Uzasadnienie „najmniejszej kontrolki":** rozwiązanie reużywa istniejący panel „Dodaj pozycję
planu" (jeden komponent, dwa tryby) zamiast projektować nowy typ wiersza z ikonami w i tak ciasnej
siatce `210px 130px 1fr 130px 190px`, która nie ma miejsca na dodatkową kolumnę.

---

## 5. „Kosz kończy regułę, nie kasuje" — co to znaczy dla człowieka

`testy/test_nosniki.py::test_kosz_planu_KONCZY_regule_a_nie_kasuje` pilnuje, że w spisie tras nie
ma żadnej trasy `DELETE .../plan...` — silnik ma funkcję kasującą (`usun_plan`), świadomie odciętą
od interfejsu (Z-9, `../AI CFO/docs/2026-08-28-przekazanie-do-implementacji.md` §5).

**Po ludzku:** gdy Darek „kończy" pozycję planu (np. Czesne 660 zł/mc) w grudniu — **historia się
nie zmienia**. Październik i listopad nadal pokazują, że Czesne było zaplanowane na 660 zł i tyle
wykonano. Zmienia się wyłącznie **przyszłość**: od bieżącego miesiąca w przód ta pozycja przestaje
się pojawiać w planie. Element opisany w §4.2 realizuje to dosłownie — stąd wymóg nazwy „Zakończ",
nie „Usuń", i zdanie potwierdzenia nazywające zakres skutku wprost.

---

## 6. Defekt układu w ramce — „Historia", stan pusty

**Sekcja „Historia" na `Budzet.dc.html` (linie 148–151) niesie defekt układu — nie jest wzorcem
do naśladowania.** Dwa akapity stanu pustego („W październiku nie ma jeszcze czego poprawiać." +
wyjaśnienie) są bezpośrednim dzieckiem `<div style="display: grid; grid-template-columns: 110px
130px 1fr 160px 160px">` — siatki zaprojektowanej pod wiersz danych (Data/Kwota/Opis/Kategoria/
Akcje), nie pod prozę. Efekt: tytuł stanu pustego łamie się w wąskiej kolumnie 110 px (zrzut
`makiety/zrzuty/Budzet-ramka-dowod-W9.png` to potwierdza wizualnie — kolumna tytułu wygląda jak
pionowy słupek liter).

**Kontrast — jak wygląda to poprawnie na TEJ SAMEJ ramce:** sekcja „Przychody i oszczędności"
(linia 121) ma analogiczny stan pusty, ale jego `<p>` stoi **poza** siatką kolumn, pełnej
szerokości — to jest wzorzec.

**Wiążące polecenie dla Jacka: buduj stan pusty Historii wg wzorca „Przychody i oszczędności"
(`<p>` pełnej szerokości poza siatką kolumn), NIE wg dosłownego układu ramki dla tej sekcji.**
Ramka **niesie defekt** w tym jednym miejscu — nie poprawiam jej pliku (zakaz zadania), ale
zapisuję to tutaj, żeby bramka odwzorowania (`docs/PRD.md` §12.7 — porównanie maszynowe zrzutu
z ramką) nie została odczytana jako wada wykonania, gdy Jack świadomie odstąpi od tego jednego
fragmentu ramki.

### 6.1 Kontrola liczności — czy wzorzec powtarza się na pozostałych 41 ramkach

Sprawdzone parserem drzewa HTML (`html.parser`, nie regexem na liniach — żeby poprawnie widzieć
rodzica, nie tylko sąsiedztwo linii), na **42 plikach** `makiety/*.dc.html`:

```
ramek sprawdzonych: 42
ramek z trafieniem (<p> jako dziecko <div grid-template-columns> z >=3 kolumnami
i >=2 kolumnami wąskimi w px <=200px): 2
  Budzet-zrodlo.dc.html:149  szablon='110px 130px 1fr 160px 160px'
  Budzet-zrodlo.dc.html:150  szablon='110px 130px 1fr 160px 160px'
  Budzet.dc.html:150  szablon='110px 130px 1fr 160px 160px'
  Budzet.dc.html:151  szablon='110px 130px 1fr 160px 160px'
```

**Wzorzec siedzi wyłącznie w tej jednej ramce** (źródło + finalna wersja tego samego ekranu) —
**0 dodatkowych trafień w pozostałych 40 plikach**. Pierwszy, szerszy trop (dowolny `<p>` jako
dziecko dowolnego `grid-template-columns`, bez warunku na wąskie kolumny) dał dodatkowo
`Ustawienia.dc.html`/`Ustawienia-zrodlo.dc.html` — **sprawdzone ręcznie i to jest fałszywy trop**:
tam siatka to symetryczny układ prozy `1fr 1fr` (dwa akapity opisowe obok siebie, sekcja „Czego tu
nie ma"), nie tabela danych z wąskimi kolumnami — nic tam nie łamie się w wąskiej kolumnie.
Jack nie musi nic poprawiać poza Budżetem.

---

## 7. Kontrolka „Wybrany miesiąc" — element ramki bez pokrycia, POZA ZAKRESEM

Sprawdzone nośniki: `docs/PRD.md` (§10.2, §10.3), `docs/plan-wydawania.md`, `docs/plan-chmura-
2026-08-29.md`, `../AI CFO/docs/makiety-v2/decyzje-projektowe.md`. Fraza „Wybrany miesiąc" pojawia
się wyłącznie w kontekście **Raportów** (nastawa zakresu okresu, np. „Wybrany miesiąc · Ostatnie
3 miesiące · Ostatnie 6 miesięcy..." — `docs/PRD.md` w.7329) — **nigdzie w opisie ekranu Budżet**.

**Rozstrzygnięcie: to NIE jest zakres do zbudowania.** §3.6 czyni zakresem to, co ramka **obiecuje
człowiekowi** — element bez opisanej funkcji niczego nie obiecuje; obiecałby ją dopiero wtedy, gdy
ktoś powie, co robi klik. Kontrolka bez treści za sobą nie generuje pracy dla Maxa ani Jacka.

**Wiążące polecenie: Jack buduje na Budżecie wyłącznie jeden selektor okresu — „październik 2026"
(nastawa realnie opisana i używana w całym dokumencie). Drugi element z ramki („Wybrany miesiąc")
zostaje pominięty w budowie** do czasu, aż ktoś nazwie jego funkcję — wtedy wraca jako osobny
przyrost zakresu, nie jako część W9.

---

## 8. Trzy trasy do wyłączenia starej zakładki

```
len(WARUNEK_WYLACZENIA) = 5
POST   /api/wpisy                ZBUDOWANA
DELETE /api/wpisy/{id}           ZBUDOWANA
PUT    /api/plan/{id}            BRAK
POST   /api/plan                 BRAK
POST   /api/plan/{id}/zakoncz    BRAK
```

Brakujące trzy pokrywają się w 100% z trasami Budżetu (§3). Budując Budżet, Max jednocześnie
domyka bramkę wyłączenia starej zakładki — nie ma tu osobnej pracy do zrobienia później.

---

## 9. Znaleziska dodatkowe — §3.5

„Poduszka finansowa 30 000,00 zł" na ramce nie mówi, że to liczba WYLICZONA — a `docs/PRD.md`
§10.3 (S-2) już rozstrzygnęło: próg = 6× wydatki niezbędne, **liczony**, z jawnym oznaczeniem, gdy
nadpisany ręcznie. **Jack buduje wg S-2 (liczba wyliczona + widoczne oznaczenie ewentualnego
nadpisania ręcznego), nie wg literalnego zapisu ramki** — to rozstrzygnięcie już istnieje w PRD,
zapisane tutaj, żeby nie zniknęło przy budowie tego konkretnego kafelka.

„Ryczałt": **zero trafień** w `Budzet.dc.html` i `Budzet-zrodlo.dc.html` (`grep -i` — exit 1).
Ramka dotrzymuje reguły projektu.

---

## 10. Czego ten dokument NIE objął

- Poprawność liczb podatkowych/ZUS widocznych na ramce (rezerwa 7 696,65 zł) — domena silnika.
- Kontrast barw i progi (P) z §12.3/12.6 pomiarem narzędziowym (`kontrast.py`).
- Projekt ramki dla kontrolki wpisywania stanu konta i ekranu „Tej części jeszcze nie ma" — poza
  zakresem W9, opisane osobno przy okazji tego zadania (patrz Slack/Linear W9 — Mila, jeśli
  potrzebne osobne wpisy).

---

## 11. Korekta ramki po W9c — bramka odwzorowania (Mila, 2026-08-29, wieczór)

**Zgłoszenie Olivera:** ekran zbudowany (`Jack`, głowa `2b2ef3b`) i działa; bramka odwzorowania
czerwona: **26,10 %** wobec ramki wiążącej, próg 2 %. Trzy przyczyny zmierzone, wszystkie po
stronie ramki. Poprawiam `makiety/Budzet.dc.html` i `makiety/Budzet-zrodlo.dc.html` — **nie
ruszam** `interfejs/app/budzet/`, silnika ani tras.

### 11.1 Poprawka 1 — stan pusty „Historii" (opisana już w §6 wyżej)

Wykonana: usunięta `display: grid; grid-template-columns: 110px 130px 1fr 160px 160px;
column-gap: 24px;` z kontenera dwóch akapitów stanu pustego — zostaje `padding-bottom: 6px;
border-bottom: 1px solid ...`, dokładnie jak w §6 wskazano. Zgodne z wzorcem „Przychody
i oszczędności" (pełna szerokość, poza siatką).

### 11.2 Poprawka 2 — Faktura 1/2026: rozstrzygnięcie FUNKCJA, nie treść przykładowa

**Sprawdzone nośniki przed rozstrzygnięciem** (§3.10): `docs/PRD.md` §10.2 (inwentarz funkcji
Budżetu — nie wymienia świadomości o fakturach), `api/trasy.py` (komentarz `GET /api/budzet`:
„kafelki planu, bilans, plan kontra wykonanie, cele" — bez faktur), `interfejs/lib/kontrakt.ts`
(`DaneBudzetu` — zero pól o numerze/stanie faktury), `interfejs/narzedzia/dane-wzorcowe.mjs`
(zero wzmianki o fakturze w ogóle — w odróżnieniu od Kredytów, gdzie autor zostawił wyjaśnienie,
tu nie ma nic).

**Rozstrzygnięcie: to jest FUNKCJA, nie treść przykładowa.** Trzy powody: **(1)** zdanie pojawia
się DWA razy, w dwóch różnych miejscach ekranu (bilans planu i „Przychody i oszczędności"),
z wewnętrznie spójnym faktem (faktura 1/2026, nieopłacona, wpłynie po oznaczeniu na karcie Firma)
— to wzorzec świadomej, powtórzonej informacji, nie przypadkowy przykład; **(2)** treść odpowiada
na realny mechanizm uczciwości tej aplikacji (§12.5 „zaufanie do liczby" — wyjaśnienie, dlaczego
plan przychodów wynosi 0,00 zł, mimo że istnieje realna, nieujęta jeszcze wpłata) — dokładnie
klasa informacji, którą ten projekt chce pokazywać, nie dekoracja; **(3)** numer „1/2026" to
realna, pierwsza faktura Darka (cytowana też w `docs/PRD.md` §10.3, S-1, przy okazji ekranu Firma
i Doradcy) — nie placeholder wymyślony na potrzeby makiety.

**Decyzja: zdania ZOSTAJĄ na ramce bez zmian.** Zgodnie z poleceniem Olivera nie zdejmuję funkcji,
której ramka obiecuje. **Zakres dla Maxa, z progiem:** `DaneBudzetu` potrzebuje pola niosącego
świadomość o nieopłaconych fakturach bieżącego miesiąca (numer, kwota, stan), zasilanego z danych
karty Firma (`GET /api/firma/faktura/{numer}` już istnieje w spisie tras). **Próg: gdy ekran Firma
i jego trasy zostaną zbudowane (Plasterek 3)** — naturalna kolejność, bo dziś Firma sama nie ma
jeszcze zbudowanej trasy zapisu faktur do sprawdzenia. Do tego czasu jest to **nazwana, przyjęta
luka** — nie cichy dług.

### 11.3 Poprawka 3 — „Kredyty 1 624,81 zł (1 i 12 X)"

**Weryfikacja przesłanki komendą, własny odczyt** (nie tylko cytat z PRD), na oryginalnej bazie
poprzednika:

```
$ sqlite3 "../AI CFO/cfo_database.db" "select kategoria, kwota_planowana, dzien, co_ile_miesiecy
  from plan_budzetu where rok=2026 and powtarzalna=1
  and (10-miesiac)%co_ile_miesiecy=0 and 10>=miesiac order by dzien;"
Kredyty|319.76|1|1
Kredyty|1305.05|12|1
Energia Elektryczna|330.00|20|2
Czesne|660.00|25|1
```
319,76 + 1 305,05 = **1 624,81** — potwierdzone: ramka scaliła dwie osobne reguły planu (dwa
różne dni) w jeden nawias. `PozycjaPlanu.dzien: number | null` niesie **jeden** dzień —
niemożliwe do zbudowania jak napisano.

**Nośnik pierwotny znaleziony PRZED poprawką** (§3.10): `interfejs/narzedzia/dane-wzorcowe.mjs`
w.224–235 już opisuje dokładnie ten problem i już rozstrzyga wartość: *„wzorzec niesie jedną
pozycję Kredytów o kwocie z ramki i dniu `1`. Ekran napisze więc «(1 X)» tam, gdzie ramka pisze
«(1 i 12 X)» — różnica NAZWANA, nie zamieciona."* **Poprawka trzyma się tego rozstrzygnięcia
co do joty** — nie wybieram własnej wartości (rozważałam dzień 12 z powodu „jeszcze czeka",
bo dzień 1 już minął przy „dziś = 6 X"; **odrzucone**, bo wzorcowy zestaw danych, który Jack już
zbudował, ma dzień `1` na stałe, i to on rozstrzyga zgodność pikselowy, nie moja interpretacja).

**Wykonane:** `(1 i 12 X)` → `(1 X)` w obu plikach, kwota **bez zmian** (1 624,81 zł — zgodna
z kafelkiem i wierszem tabeli, żadna inna liczba nie rusza się).

### 11.4 Znalezisko dodatkowe (nienazwane przez Olivera) — kolejność pozycji w zdaniu

Przy weryfikacji poprawki 3 znalazłam **czwartą, pokrewną przyczynę** tej samej klasy (§3.2,
„jeden nośnik" — tu dla KOLEJNOŚCI, nie dla wartości): ekran wymienia pozycje w kolejności
Czesne → Energia Elektryczna → Kredyty (alfabetycznie, zgodnie z porządkiem silnika), a ramka
niosła Kredyty → Energia Elektryczna → Czesne (po dniu). Nośnik, sprawdzony przed poprawką:
`interfejs/narzedzia/dane-wzorcowe.mjs` w.294–296: *„Zdanie narracyjne wymienia pozycje w tej
samej kolejności, w której je dostaje — sortowanie po dniu byłoby DRUGIM nośnikiem porządku,
obok tego, który ustala silnik."* **Poprawione**: kolejność w ramce zmieniona na alfabetyczną,
zgodną z silnikiem. Wkład w liczbę procentową okazał się mały (ta sama długość linii, brak zmiany
zawijania) — poprawka warta zrobienia dla zgodności reguły, nie dla samego progu.

### 11.5 Sprawdzone i ŚWIADOMIE COFNIĘTE — zegar w nagłówku „· 09:40"

Przy pomiarze zauważyłam, że nagłówek ramki niesie *„6 października 2026 · 09:40"*, a
`interfejs/lib/kwota.ts` w.116–121 dokumentuje **już podjętą** decyzję Z7: *„GODZINY TU NIE MA
I TO JEST DECYZJA, NIE BRAK (...) Wraca w chwili, gdy kontrakt zacznie nieść znacznik czasu
odczytu, a nie samą datę."* Zbudowany ekran istotnie pokazuje wyłącznie datę, bez godziny —
zmierzone (`playwright`, tekst węzła): `"6 października 2026"`.

**Spróbowałam poprawić `Budzet.dc.html` bezpośrednio — i COFNĘŁAM tę zmianę.** Powód: tekst
„· 09:40" **nie jest treścią ramki źródłowej** — wstrzykuje go `wskaznik_daty()` w
`makiety/buduj-makiety.py:279-282`, ze stałych `WSKAZNIK_DZIEN`/`WSKAZNIK_GODZINA` (w.275–276),
**identycznie do KAŻDEJ finalnej ramki z pełnym paskiem** (`z_paskiem()`) — potwierdzone:
ten sam ciąg „6 października 2026 · 09:40" siedzi też w `Main.dc.html` i `Ksiegowanie.dc.html`,
czyli w dwóch ramkach **już przechodzących** bramkę (0,07 %, 0,12 %). Ręczna edycja samego
`Budzet.dc.html` byłaby **drugim nośnikiem** tej stałej (§3.2) i zostałaby cicho nadpisana przy
najbliższym `python3 buduj-makiety.py` (bez `--kontrola`) — dokładnie dług ukryty, przed którym
ostrzega CLAUDE.md. **Potwierdzone `--kontrola`:** po cofnięciu — `ROZBIEZNOSCI: 0`, kod wyjścia 0.

**Nazwane, NIE wykonane w tym zadaniu** (poza zakresem — dotyczy Main i Ksiegowanie, nie tylko
Budżetu): właściwa poprawka to `WSKAZNIK_GODZINA` (i separator „· ") usunięte z
`wskaznik_daty()` w `buduj-makiety.py`, a potem **pełna regeneracja** wszystkich finalnych ramek
przez `buduj-makiety.py` (nie `--kontrola`) — dotknie też `Main.dc.html` i `Ksiegowanie.dc.html`.
**Próg: osobne zlecenie, bo zakres wykracza poza ekran Budżet** i wymaga ponownego zmierzenia
dwóch już przechodzących bramek.

### 11.6 Bramka odbioru — wynik po poprawkach

```
$ cd makiety && python3 buduj-makiety.py --kontrola
PLIKOW .DC.HTML SPRAWDZONYCH LACZNIE: 42
ROZBIEZNOSCI: 0
(kod wyjścia 0)

$ cd interfejs && node narzedzia/porownaj-z-makieta.mjs Budzet Budzet
RÓŻNICA: 0,00%   PRÓG: 2,00%   WYNIK: w progu.          (kontrola narzędzia — sama ze sobą)

$ node narzedzia/porownaj-z-makieta.mjs Budzet Main
RÓŻNICA: 31,26%   PRÓG: 2,00%   WYNIK: PRÓG PRZEKROCZONY. (kontrola narzędzia — inny ekran, liczba dwucyfrowa)

$ node narzedzia/porownaj-z-makieta.mjs Budzet http://localhost:3000/budzet --wzorzec
Ramka:  Budzet  1440x1266 px
Ekran:  http://localhost:3000/budzet  1440x1205 px  (źródło danych: WZORZEC, znacznik znaleziony)
Porównanych pikseli: 1 823 040, różniących się: 251 923
RÓŻNICA: 13,82%   PRÓG: 2,00%   WYNIK: PRÓG PRZEKROCZONY.
```

**13,82 %, nadal powyżej progu 2 %.** Co ją niesie — zmierzone z obrazu różnicy
(`makiety/zrzuty/Budzet-roznica-W9d-po-poprawkach.png`), nie z domysłu: rozjazd zaczyna się
dokładnie w akapicie „Przychód z faktury 1/2026..." (§11.2, świadomie NIE naprawiony — funkcja,
nie treść przykładowa) i stamtąd rozchodzi się kaskadą pionowego przesunięcia na wszystko poniżej
(tabela planu, cele, historia, stopka) — wysokość ramki 1266 px wobec ekranu 1205 px, różnica
61 px, zgodna co do rzędu wielkości z „54 px kaskady" zmierzonymi przez Olivera przed moimi
poprawkami. Poprawki 1, 3 i 4 (§11.1, 11.3, 11.4) są w obrazie różnicy **widoczne jako zgodne**
(ten sam tekst po obu stronach, przesunięty wyłącznie przez kaskadę z §11.2) — nie generują już
własnego rozjazdu treści.

**To jest jedna liczba i jedna, w pełni nazwana przyczyna** (§11.2) — zgodnie z poleceniem
Olivera, idzie do Darka jako nazwane odstępstwo z wpisem do PRD, nie jako moja decyzja o zamknięciu
bramki. Rozstrzygnięcie progu (czy 2 % obowiązuje mimo świadomie zachowanej funkcji bez pokrycia
w kontrakcie) należy do niego.

**Czego to zadanie NIE objęło:** poprawki `wskaznik_daty()` w `buduj-makiety.py` (§11.5) i
regeneracji Main/Ksiegowanie; regeneracji fizycznego pliku `Budzet.dc.html` narzędziem
`buduj-makiety.py` bez `--kontrola` (edycje wykonane ręcznie w obu plikach, `-zrodlo` i finalnym,
zweryfikowane zgodne przez `--kontrola`, ale nie przepuszczone przez sam generator — różnica
czysto proceduralna, wynik identyczny).
