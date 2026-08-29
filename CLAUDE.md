# CLAUDE.md — konstytucja projektu „Doradca Finansowy"

Plik ładowany przy starcie każdej sesji w tym katalogu. Nadrzędna wobec niego jest wyłącznie
konstytucja firmy (`../CLAUDE.md`). Właściciel: Darek. Zmiana wymaga jego sign-offu.

**Wersja:** v1.1 · 2026-08-29 — **tryb pracy: implementacja bez udziału Darka** (nowa sekcja 8).
Decyzja Darka 2026-08-29, godz. 00:32. Trzy reguły: plan puszczony przez Darka wykonuje zespół do
końca; Oliver nadzoruje i powołuje specjalistów, jeden agent naraz we własnym oknie kontekstowym;
output wyłącznie niezbędny — agent odzywa się tylko wtedy, gdy czegoś od Darka potrzebuje.
**Zakres: WYŁĄCZNIE ten projekt.** Konstytucja firmy (`../CLAUDE.md`) bez zmian — w szczególności
jej sekcja 13 punkt 7 („agent wykonuje, Ty potwierdzasz każdy krok") obowiązuje wszędzie indziej.

**Wersja:** v1.0 · 2026-08-28 — pierwsza wersja. Projekt założony decyzją Darka z 2026-08-28
(godz. 23:2x–23:4x): nowy start w pustym katalogu, silnik przeniesiony z `../AI CFO`.

---

## 1. Czym to jest

Osobisty doradca finansowy dla **jednej osoby** — Darka — prowadzącego jednoosobową działalność
gospodarczą w Polsce. Aplikacja odpowiada na trzy pytania: **czy mam pieniądze**, **co mnie zaraz
uderzy**, **co mam z tym zrobić**.

Poprzednik: `../AI CFO` — wygaszany. Jego dokumenty są nośnikiem decyzji i wiedzy; jego kod
NiceGUI (`pulpit/`) nie jest odniesieniem ani wizualnym, ani architektonicznym.

Dokument główny: **`docs/PRD.md`**. Kolejność prac: **`docs/plan-wydawania.md`**.

---

## 2. Nastawy użytkownika — przeczytaj to przed policzeniem czegokolwiek

Pięć faktów, od których zależy **każda kwota** w tej aplikacji. Nie zgaduj ich i nie wyprowadzaj
z kodu — kod bywa nieaktualny.

| Nastawa | Wartość | Skąd |
|---|---|---|
| **Forma opodatkowania 2026 i lata następne** | **SKALA PODATKOWA** (zasady ogólne) | decyzja Darka, potwierdzona pięciokrotnie 2026-08-28 |
| **Składki ZUS** | **duży ZUS** (pełne składki), z chorobową | j.w. |
| **VAT** | czynny płatnik, 23%, **rozliczany memoriałowo** — obowiązek z chwilą **wystawienia** faktury | D-35 |
| **Data rozpoczęcia działalności** | **2026-09-01** (wznowienie po zawieszeniu z 2023) | D-22 |
| **Horyzont danych** | od IX 2026 w przód; 204 wpisy z 2025 wchodzą **wyłącznie jako historia** | D-23 + decyzja 2026-08-28 |

**RYCZAŁT JEST WADĄ, NIE OPCJĄ DOMYŚLNĄ.** W poprzedniej aplikacji cztery miejsca liczyły i mówiły
ryczałtem bezwarunkowo, przez co podawała kwoty podatku wyliczone formą, której Darek nie ma.
Słowo „ryczałt" wolno tu zobaczyć w dokładnie dwóch rolach: jako **opcję w porównaniu form**
i jako **wiedzę o prawie w rejestrze stawek**. Każda inna rola jest wadą do zgłoszenia.

---

## 3. Reguły twarde — łamanie ich jest wadą, nie decyzją

### 3.1 Pieniądze liczy się typem dziesiętnym, nigdy zmiennoprzecinkowym
`Decimal` w Pythonie, `NUMERIC` w bazie. Liczba zmiennoprzecinkowa w ścieżce kwoty to wada
krytyczna. Poprzednia aplikacja miała zmierzoną awarię tego typu: warstwa sieciowa zamieniała
`Decimal` na `float`, gubiła grosze i **zwracała 200**.

### 3.2 Żadna liczba nie powstaje w dwóch miejscach
Reguła o konsekwencji zewnętrznej ma **dokładnie jeden nośnik**; pozostałe miejsca ją **wołają**.
Świadomy drugi nośnik jest dopuszczalny wyłącznie z testem-strażnikiem i jawnym progiem
konsolidacji. Odłożenie bez strażnika i progu to dług ukryty, nie decyzja.

**Wyjątek nazwany (Krug):** ta reguła dotyczy **reguł**, nie **wyglądu**. Karta niosąca ostrzeżenie
o braku pieniędzy ma prawo wyglądać inaczej niż karta z datą odczytu. Przejrzystość wygrywa
z konsekwencją wizualną.

### 3.3 Żadnej stawki w kodzie
Każda liczba pochodząca z ustawy, rozporządzenia albo komunikatu ZUS mieszka w **rejestrze stawek**
(`wiedza/`), z podstawą prawną, datą odczytu i podpisem zatwierdzającego. Stawka zapisana w kodzie
silnika jest wadą.

### 3.4 Automat proponuje, człowiek zatwierdza
Czujka aktów prawnych i odczyt stron **nigdy** nie podmieniają stawki użytej do rachunku.
Podnoszą chorągiewkę „stawki mogą być nieaktualne" i pokazują: stara wartość → nowa → źródło → data.
Zatwierdza Darek. Powód zmierzony: równoległa wersja tej aplikacji miała czujkę, która przy awarii
API zwracała **akty prawne zmyślone, nieodróżnialne od prawdziwych**.

### 3.5 Etykieta opisuje liczbę, którą pokazuje
Tytuł kafelka, nagłówek kolumny i etykieta pola opisują liczbę **faktycznie wyświetlaną** — nie
pokrewną, nie tę, z której powstała, nie tę, którą kiedyś pokazywały. Gdy do kwoty wchodzi składnik
obcej natury (cudze pieniądze, rezerwa, zaokrąglenie), musi być **nazwany przy liczbie**.
Stan wyjątkowy podaje **wielkość**, nie samo słowo: „przekroczony o 859,49 zł", nie „przekroczony".

### 3.6 Makieta jest wiążącą specyfikacją — w dwóch wymiarach
**Zakres:** każda funkcja widoczna na ramce `makiety/*.dc.html` wchodzi do aplikacji.
**Wygląd:** odwzorowanie ma być zgodne co do piksela przy tej samej szerokości.
Ekran jest skończony, gdy porównanie maszynowe zrzutu z ramką przechodzi. Odstępstwo wymaga
zgody Darka i wpisu w PRD — nigdy milczącej decyzji wykonawcy.

### 3.7 Awaria do stanu użytecznego, nie do zera
Gdy padnie API, klucz albo źródło danych: aplikacja **mówi, czego brakuje i co zrobić**. Nigdy
nie pokazuje pustki ani liczby z nieznanego źródła. Doradca bez modelu językowego wydaje
**ten sam komplet rad** — model dobiera wyłącznie słowa.

### 3.8 Strażnik bez mutacji nie liczy się jako strażnik
Test przywoływany jako dowód, że reguła jest pilnowana, ma udokumentowaną mutację, która go
**czerwieni**: co zmieniono, **który test padł** (po nazwie, nie „N failed"), data. Potem mutację
się cofa. Zielona suita nie jest dowodem, że strażnik strzeże.

### 3.9 Dowód z komendy, nie deklaracja
Każde twierdzenie o stanie faktycznym (ile czegoś jest, co jest wdrożone, czy własność zachodzi)
wymaga wykonania komendy i **zacytowania jej wyjścia**. „Sprawdziłem" bez cytatu nie jest dowodem.
Twierdzenie niesprawdzalne stawia się z jawną etykietą **„niezweryfikowane"**.

### 3.10 Najpierw nośnik, potem pomiar
Ustalanie stanu faktycznego zaczyna się od pytania „który nośnik już to twierdzi" i od jego
odczytania. Znalezisko brzmi „nośnik twierdzi X, pomiar pokazuje Y", nigdy „nie wiadomo".

### 3.11 Przed działaniem nieodwracalnym: co przez to przestanie działać
Lista warunków przed skasowaniem, unieważnieniem albo wyłączeniem ma osobną pozycję
**„co przez to przestanie działać"**. Odpowiedź „niczym" pada jawnie i z pomiarem.

---

## 4. Język

- **Kod, nazwy tabel, nazwy funkcji: po polsku bez znaków diakrytycznych** (`wpisy_budzetu`,
  `policz_zaliczke`, `rdzen`). Tak jest napisany przeniesiony silnik i tak brzmią wszystkie decyzje.
- **Interfejs i dokumenty: po polsku z pełnymi znakami.**
- **Żargon tłumaczony przy pierwszym użyciu.** Darek nie jest deweloperem. Każde angielskie
  zapożyczenie i skrót wewnętrzny rozwijasz jednym nawiasem — inaczej nie może świadomie
  zaakceptować tego, co mu pokazujesz.
- **Bez emoji w prozie. Konkrety zamiast ogólników.** Kwoty, daty, ścieżki plików.

---

## 5. Mapa nośników — gdzie co mieszka

| Co | Nośnik | Uwaga |
|---|---|---|
| Wymagania produktu | `docs/PRD.md` | jedyny |
| Kolejność prac | `docs/plan-wydawania.md` | jedyny; PRD go **woła**, nie powtarza |
| Decyzje historyczne D-1…D-36 | `../AI CFO/docs/2026-08-28-przekazanie-do-implementacji.md` v1.9 | archiwalny, cytowany |
| Wygląd i zakres ekranów | `makiety/*.dc.html` + `makiety/paleta.json` | wiążąca specyfikacja |
| Uzasadnienia projektowe | `../AI CFO/docs/makiety-v2/decyzje-projektowe.md` v2.4 | archiwalny |
| Kryteria mierzalne interfejsu | `../AI CFO/docs/2026-08-28-fundament-projektowy-ui-ux.md` §6 | progi **(P)** to propozycje, nie fakty |
| Stawki podatkowe i składkowe | tabela `rejestr_stawek` w bazie, zasilana z `wiedza/` | **jedyne** źródło liczb z ustaw |
| Napisy i formatowanie kwot | `silnik/prezentacja.py` | widok **woła**, nie powtarza |
| Mapa ekranów i paska | `makiety/ekrany.py` | jedyny |

---

## 6. Czego ta aplikacja nie robi

1. Nie doradza, którą formę opodatkowania wybrać — porównuje z wypisanymi zastrzeżeniami.
2. Nie ocenia prawa do odliczenia VAT od konkretnego zakupu.
3. Nie prowadzi księgi przychodów i rozchodów, nie wysyła niczego do urzędu.
4. Nie liczy wspólnego rozliczenia z małżonkiem ani ulg — **i to jest jawna luka**, bo tam skala
   wygrywa z ryczałtem najmocniej.
5. Nie ujawnia informacji o klientach kontrahenta — narzędzia doradcy zwracają wyłącznie agregaty.
6. Nie zajmuje się instrumentami inwestycyjnymi.
7. Nie wystawia faktur.

---

## 7. Praca z Darkiem

> **To, CO w ogóle trafia do Darka, rozstrzyga sekcja 8.3 — nie ta sekcja.** Tutaj stoi wyłącznie
> forma. Sekcja 7 mówi „jak pisać", sekcja 8 mówi „czy pisać w ogóle".

1. **Krótkie polecenia („dalej", „skasuj") = wykonaj.** Nie pytaj ponownie.
2. **Jedna prośba naraz.** Instrukcje wprost: co przygotowałem, co masz zrobić, gdzie to jest,
   po co wracasz. Uzasadnienie **po** poleceniu i krótkie.
3. **Zamykaj okno przed otwarciem następnego.** Kilkadziesiąt okien naraz zabija płynność laptopa.
4. **Wersjonuj zauważalnie.** Każda iteracja istotnego dokumentu → bump wersji + changelog na górze.
5. **Obejrzyj ekran przed oddaniem.** Zielona suita nie mówi nic o wyglądzie.

---

## 8. Tryb pracy — implementacja bez udziału Darka

> **Zakres tej sekcji: WYŁĄCZNIE projekt „Doradca Finansowy".** Nie obowiązuje w SkillBridge,
> w repozytorium firmy ani w żadnym innym katalogu. Konstytucja firmy (`../CLAUDE.md`) pozostaje
> nietknięta; tam nadal obowiązuje sekcja 13 punkt 7 — *„agent wykonuje, Ty potwierdzasz każdy
> krok"*. **Tutaj ten punkt jest zawieszony** na czas wykonania planu, który Darek puścił.

Decyzja Darka 2026-08-29, godz. 00:32.

### 8.1 Darek puszcza plan. Reszta idzie bez niego

**Zatwierdzenie planu jest jedynym momentem udziału Darka w jego wykonaniu.** Od „puszczam" do
gotowego wyniku zespół agentów pracuje sam: dobiera kolejność w ramach planu, rozstrzyga
wątpliwości techniczne, naprawia to, co się nie udało, i wraca dopiero z rezultatem.

**Nie wraca po zgodę na krok, który plan już objął.** Pytanie o coś, co stoi w zatwierdzonym
planie, jest złamaniem tej reguły — nie ostrożnością.

### 8.2 Oliver nadzoruje. Jeden agent naraz, we własnym oknie

- **Oliver (COO) prowadzi wykonanie** i powołuje do poszczególnych zadań **specjalistów
  zatrudnionych w nordsignal** (`../agents/*.md`): Ethan do architektury i silnika, Max do
  backendu, Jack do interfejsu, Leo do przeglądu, Mila do projektu ekranu, Quinn do testów,
  Ryan do ryzyka i danych osobowych, Sophia do decyzji produktowych.
- **Naraz pracuje dokładnie jeden agent, we własnym oknie kontekstowym.** Oliver powołuje po
  kolei i czeka na wynik. „Maksymalnie 3–4" z wcześniejszych ustaleń jest sufitem ryzyka
  wynikającym z limitu sesji, **nie zgodą na równoległość**.
- **Oliver pilnuje głównego okna kontekstowego**, żeby nie zapełniło się przedwcześnie. Praca
  szczegółowa — czytanie plików, przebiegi testów, mutacje — dzieje się w oknie specjalisty;
  do głównego okna wraca **wynik**, nie przebieg.

### 8.2a Zasoby nordsignal — wolno korzystać ze wszystkich

Autoryzacja Darka 2026-08-29, godz. 00:36: *„możesz korzystać też z zasobów nordsignal jak
właśnie agenci, skille i reszta co będzie potrzebne"*.

| Zasób | Gdzie | Co z tego bierzemy |
|---|---|---|
| **Agenci** | `../agents/*.md` | 18 zatrudnionych; dziewięcioro wymienionych w 8.2 |
| **Skille** | `../skills/` | `operations/orkiestracja-celu.md` (runbook Olivera), `engineering/`, `backend/`, `frontend/`, `qa/`, `design/`, `product/`, `devops/` |
| **Polityki** | `../policies/` | whitelist MCP, reguły dostępowe |
| **Wzorce jakości** | `../skills/engineering/golden-adr.md`, `production-readiness.md`, `../skills/design/golden-samoocena.md` | wzorce, do których dorównuje output |
| **Wiedza z AI CFO** | `../AI CFO/docs/` | 22 dokumenty: decyzje, fundament UI/UX, analiza Kruga, kształt doradcy |

**Granica bez zmian:** korzystanie z zasobu to **odczyt i wołanie**, nie edycja. Pliki rządzenia
firmy (`../CLAUDE.md`, `../agents/*.md`, `../hooks/`) pozostają czerwoną linią — sekcja 4
konstytucji firmy. Zmiana skilla albo definicji agenta wymaga sign-offu Darka, tak jak dotąd.

### 8.3 Output: tylko to, co niezbędne

**Do Darka trafia rezultat i nic poza nim.**

**Nie piszemy:** dlaczego coś nie zadziałało · jaką drogę wybrano i dlaczego · co rozważono
i odrzucono · uzasadnień technicznych · relacji z przebiegu prac.

**Piszemy wyłącznie wtedy, gdy czegoś od Darka potrzebujemy** — decyzji, danych, dostępu,
sign-offu czerwonej linii. Wtedy: **czego potrzebujemy, po co, i co się bez tego nie wydarzy.**
Jedna prośba naraz.

Uzasadnienia, przyczyny awarii i wybory techniczne **nie znikają** — idą tam, gdzie ich miejsce:
do dokumentów w `docs/`, do opisów commitów i do `testy/MUTACJE.md`. Ślad audytowy zostaje
nienaruszony; zmienia się wyłącznie to, że nie płynie przez czat.

### 8.4 Granica — czego ta sekcja NIE zdejmuje

**Dziewięć czerwonych linii konstytucji firmy (sekcja 4) zostaje w mocy.** Wydatek, publikacja,
nowy MCP, edycja plików rządzenia, kontrakt — nadal wymagają jawnego „tak" Darka. Ta sekcja ich
nie deleguje; przeciwnie, zgodnie z 8.3 **eskalacja czerwonej linii jest jedną z niewielu rzeczy,
o których wolno napisać**, bo jest dokładnie „czegoś od Ciebie potrzebuję".

**Cisza nigdy nie autoryzuje czerwonej linii.**

### 8.5 Co przez to przestanie działać

Pozycja obowiązkowa (§3.11). Wypisana przed wykonaniem, nie po.

| Co znika | Skutek |
|---|---|
| Wczesne ostrzeżenie w czacie | Darek dowie się o źle obranym kierunku **z wyniku**, nie w trakcie. Zostaje mu jedno narzędzie: odrzucić rezultat i cofnąć plan. Koszt pomyłki rośnie o długość plasterka |
| Wyjaśnienia wyborów technicznych na bieżąco | ocena, czy wybór był trafny, przenosi się na przegląd dokumentów i commitów — czyli **po fakcie**. Nie ma następcy w czasie rzeczywistym |
| Potwierdzanie każdego kroku | znika ostatnia ludzka pauza przed operacją, której plan nie przewidział. W tym repozytorium nie ma bramek `PreToolUse`, więc **nic jej nie zastępuje** |
| Równoległość agentów | czas zegarowy rośnie. To jest **cena zapłacona świadomie** za to, że dwóch agentów nie pisze do jednego pliku |

**Nie przestaje działać:** dziennik audytowy, historia gita, dokumenty w `docs/`, ślad mutacji,
strażnicy i wszystkie bramki odbioru z `docs/PRD.md` §12.
