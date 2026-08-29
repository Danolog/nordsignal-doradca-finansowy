# Przebiegi mutacyjne — dowód, że strażnicy potrafią się zaczerwienić

**Po co ten plik.** Konstytucja projektu §3.8: test przywołany jako dowód, że reguła jest
pilnowana, wymaga udokumentowanej mutacji, która go **czerwieni** — z nazwą testu, nie z „N failed".
Zielona suita nie jest dowodem, że strażnik strzeże.

**Jak wykonywano.** W kopii drzewa poza repozytorium (`scratchpad/mutacje`), z czyszczeniem
skompilowanego kodu przed każdym przebiegiem. Kopia jest wymogiem, nie ostrożnością: równolegli
audytorzy na jednym drzewie wstrzykują sobie nawzajem mutacje, a czerwony test z wartością, której
nie ma w repozytorium, to cudza mutacja, nie defekt.

---

## Przebieg 2026-08-29 — `wiedza/rejestr.py`

Kontrola przed mutacjami: **12 passed**.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M1** | `obowiazujaca` przepuszcza wiersze `proponowana` (warunek `== "zatwierdzona"` → `!= "wycofana"`) | `test_propozycja_automatu_NIE_dociera_do_silnika` · `test_brak_stawki_MOWI_o_czekajacych_propozycjach` | **czerwony** |
| **M2** | `wartosc_jako_ulamek` zwraca procent bez dzielenia przez 100 | `test_procent_i_ulamek_daja_TE_SAMA_stope` | **czerwony** |
| **M3** | `Stawka.__post_init__` przestaje wymagać podpisu przy statusie `zatwierdzona` | `test_zatwierdzona_bez_podpisu_NIE_POWSTAJE` | **czerwony** |
| **M4** | `obowiazuje()` ignoruje koniec okresu (`return True` zamiast porównania z `obowiazuje_do`) | — **przed poprawką: ŻADEN** | **ZIELONY — luka** |
| **M4′** | ta sama mutacja po dopisaniu strażnika | `test_stawka_PO_WYGASNIECIU_nie_obowiazuje` | **czerwony** |

Kontrola po cofnięciu wszystkich mutacji: **12 passed**.

---

## Co znalazła M4 — i dlaczego to jest najważniejsza pozycja tej tabeli

**Koniec okresu obowiązywania nie miał ani jednego strażnika.** Mutacja kasująca warunek
`obowiazuje_do` przeszła przez całą suitę **na zielono**.

Test, który wyglądał, jakby tego pilnował (`test_rachunek_za_wrzesien_liczy_sie_stawka_wrzesniowa`),
w rzeczywistości sprawdzał co innego: stawkę przyszłą odsiewa w nim kontrola **początku** okresu,
więc mutacja na końcu okresu nie zmieniała jego wyniku.

**Skutek, gdyby to zostało:** stawka uchylona ustawą liczyłaby kwoty w nieskończoność, a rejestr
wyglądałby na zadbany — bo każda pozycja miałaby datę, źródło i podpis. Dokładnie ten rodzaj wady,
którego czytanie kodu nie wykrywa, bo kod robi to, co deklaruje jego nazwa.

**Wniosek procesowy:** mutacja, która nie czerwieni niczego, jest **wynikiem**, nie porażką
przebiegu. Zapisuj ją i domykaj lukę — nie powtarzaj mutacji do skutku, aż któraś zaświeci.

---

## Zasada przy dopisywaniu kolejnych

1. **Wymagaj czerwieni po nazwie testu**, nigdy po „N failed". W poprzednim projekcie
   **sześć razy** mutacja z planu nie zaczerwieniła wskazanego testu, a licznik i tak się zmienił.
2. **Jedna mutacja na przebieg**, z czyszczeniem skompilowanego kodu między nimi. Dwie mutacje tej
   samej długości w tej samej sekundzie potrafią uruchomić stary kod bajtowy.
3. **Mutacja się cofa** i kontrola po cofnięciu wraca do stanu wyjściowego — inaczej nie wiadomo,
   czy czerwień pochodziła z mutacji, czy z czegoś, co zostało po drodze.

---

## Przebieg 2026-08-29 — strażnicy jednego nośnika (`testy/test_nosniki.py`)

Kontrola przed mutacjami: **19 passed**.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M5** | `interfejs/lib/ekrany.ts` dostaje `Księgowanie` jako dziesiątą pozycję paska | `test_mapa_ekranow_NIE_ROZJECHALA_sie_miedzy_jezykami` · `test_ksiegowanie_NIE_JEST_pozycja_paska` | **czerwony** |
| **M6** | ktoś poprawia barwę papieru ręcznie w `paleta.css` (`#FBECD5` → `#F3E4CD`) | `test_paleta_css_ZGADZA_SIE_z_paleta_json` | **czerwony** |
| **M7** | tekst podstawowy wraca na 13 px — powrót znaleziska Z-4 | `test_tekst_podstawowy_NIE_JEST_ponizej_progu_11pt` | **czerwony** |
| **M8** | dopisana trasa `DELETE /api/plan/{id}` — kasowanie zamiast kończenia reguły | `test_kosz_planu_KONCZY_regule_a_nie_kasuje` | **czerwony** |

Kontrola po cofnięciu: **19 passed**.

**Co te cztery mutacje razem pokazują.** Trzy z nich (M5, M6, M8) to nie są błędy programistyczne —
to **cofnięcie decyzji Darka po cichu**: P-3 (księgowanie nie jest pozycją paska), wybór barwy
papieru (D-3) i Z-9 (kosz kończy regułę, nie kasuje historii). Każda wyglądałaby w przeglądzie
jak porządkowanie. Strażnik jest tu pamięcią decyzji, nie kontrolą składni.

---

## Przebieg 2026-08-29 — odczyt stawek ze stron (`testy/test_odczyt_stron.py`)

Kontrola przed mutacjami: **26 passed** (w tym jeden test z siecią).

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M9** | powrót gwiazdki przy grupie tysięcy we wzorcu liczby (`5652` → `565`) | — **przed poprawką: ŻADEN** | **ZIELONY — luka** |
| **M9′** | ta sama mutacja po dopisaniu strażnika samego wzorca | `test_wzorzec_liczby_SAM_W_SOBIE_bierze_wszystkie_cyfry` | **czerwony** |
| **M10** | częściowy odczyt zamiast błędu (regułą bez trafienia milczy) | `test_regula_bez_trafienia_PODNOSI_BLAD_zamiast_milczec` | **czerwony** |
| **M11** | porównanie przestaje zamieniać procent na ułamek | `test_porownanie_NIE_MYLI_procentu_z_ulamkiem` | **czerwony** |

Kontrola po cofnięciu: **27 passed**.

### Co znalazła M9 — strażnik pilnowany przez coś innego, niż deklarował

Test `test_liczba_bez_separatora_czytana_w_CALOSCI` twierdził, że pilnuje wzorca liczby.
Mutacja przywracająca wadę **nie zaczerwieniła go**: czyta on przez regułę zakończoną frazą `zł`,
która zmusza wyrażenie do nawrotu i **sama naprawia błąd**. Wzorca pilnowała więc kotwica jednostki,
a nie ten test.

To jest ta sama klasa wady co M4: strażnik, który przechodzi z właściwego powodu, jest
nieodróżnialny od strażnika, który przechodzi z niewłaściwego — dopóki nie spróbujesz go złamać.
Domknięcie: osobny test mierzący wzorzec **bezpośrednio**, na napisie bez jednostki po liczbie,
czyli w warunkach, w których nic go nie ratuje.

### Dwie wady wykryte pomiarem w trakcie budowy, nie mutacją

1. **Wzorzec liczby urywał „5652" na „565"** — podstawa składek dziesięciokrotnie za niska,
   wyglądająca poprawnie. Wykryte przez porównanie odczytu z rejestrem.
2. **Tekst wzorcowy w teście był parafrazą, nie cytatem.** Wyrażenie sprawdzało się na tekście
   napisanym pod nie — narzędzie pomiarowe mierzyło własną podłogę. Zastąpione **prawdziwym
   wycinkiem żywej strony**, pobranym przez ten sam moduł, który testuje.
3. **`ł` w surowym łańcuchu Pythona nie jest literą „ł".** Wzorzec z `r"składek"` szuka
   dosłownego ciągu `składek` i nie trafi nigdy — przy czym wygląda poprawnie w przeglądzie.

---

## Przebieg 2026-08-29 — Z1, ekran `Księgowanie` (`testy/test_ekran_ksiegowanie.py`)

Kopia drzewa: `scratchpad/mutacje-z1` (poza repozytorium). Czyszczenie `__pycache__` przed każdym
przebiegiem — dwie mutacje tej samej długości w tej samej sekundzie potrafią uruchomić stary
skompilowany kod, więc wymagano, żeby padł **dokładnie ten** strażnik, który miał paść.

Kontrola przed mutacjami: **36 passed**.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M1** | `napisy.ts`: `bezZnaku` → `"Kwota bez jednostki."` (zdejmuje frazę z ramki) | `test_kazda_fraza_z_ramki_JEST_na_ekranie` · `test_podpis_bez_znaku_i_pytanie_o_minus_MOWIA_TO_SAMO` | **czerwony** |
| **M2** | `page.tsx`: dopisana kwota `274,06 zł` wprost w komponencie | `test_ekran_NIE_MA_wpisanej_recznie_kwoty` | **czerwony** |
| **M3** | `page.tsx`: skasowany `autoFocus` z pola kwoty | — **przed poprawką: ŻADEN** | **ZIELONY — strażnik-atrapa** |
| **M3′** | ta sama mutacja po naprawie strażnika | `test_kursor_STOI_w_polu_kwoty_po_wejsciu` | **czerwony** |
| **M4** | `powloka.css`: `font-size: 15px` → `13px` | `test_tekst_podstawowy_NIE_JEST_ponizej_progu_11pt` | **czerwony** |
| **M5** | `dane/ksiegowanie.ts`: `Zdrowie` → `Aaa` (ogon przestaje być alfabetyczny) | `test_pasmo_ma_PIETNASCIE_kategorii_w_kolejnosci_z_ramki` | **czerwony** |
| **M6** | `page.tsx`: brzmienie „Podaj kwotę." wpisane w komponent zamiast wołane z nośnika | `test_siedem_brzmien_bledu_MA_JEDEN_nosnik` | **czerwony** |

Kontrola po cofnięciu wszystkich mutacji: **36 passed**.

### Co znalazła M3 — strażnik, który pilnował komentarza

`test_kursor_STOI_w_polu_kwoty_po_wejsciu` szukał słowa `autoFocus` **w całym pliku**. Nad
komponentem stoi komentarz wyjaśniający, że to właśnie `autoFocus` zdejmuje jedno z trzech
kliknięć — i to on wystarczał, żeby test przeszedł. Skasowanie samego atrybutu dało **36 passed**.

Gdyby to zostało: bramka „trzy kliknięcia do zapisu" (§41.1 specyfikacji) mogłaby zniknąć przy
dowolnym późniejszym refaktorze, a suita nadal meldowałaby sukces — przy czym komentarz w kodzie
twierdziłby dalej, że bramka jest spełniona.

**Domknięcie:** `_bez_komentarzy()` zdejmuje `//…` i `/*…*/` przed każdym sprawdzeniem obecności
frazy w źródle. Ta sama funkcja objęła `test_kazda_fraza_z_ramki_JEST_na_ekranie`
i `test_ekran_NIE_ZAMIENIA_kwoty_na_liczbe`, bo miały dokładnie tę samą dziurę.

### Sprostowanie strażnika z Z0 — `test_tekst_podstawowy_NIE_JEST_ponizej_progu_11pt`

Test szukał rozmiaru wzorcem `font:\s*(\d+)px`, czyli **wyłącznie w zapisie skrótowym**.
`powloka.css` przeszła w Z1 na zapis rozdzielony (`font-family` + `font-size`), bo skrót
`font: 15px/1.5` narzuca wysokość wiersza, której ramka nie ma — i wtedy strażnik przestał
znajdować cokolwiek, czerwieniąc się przy **poprawnym** kodzie. Wzorzec rozszerzono do
`font(?:-size)?:\s*(\d+)px`. To rozszerzenie zakresu, nie osłabienie — dowodzi tego M4, która
po zmianie nadal czerwieni ten test.

### Czego ten przebieg NIE objął

**Bramki odwzorowania** (`porownaj-z-makieta.mjs`) nie mutowano w tym przebiegu — jej dwustronna
kontrola pochodzi z Z0 (ramka wobec siebie 0,00%, dwie różne ramki 23,67%) i została **powtórzona**
przed użyciem narzędzia jako dowodu: `Ksiegowanie` wobec `Ksiegowanie` = **0,00%**, 1 399 680
porównanych pikseli, 2026-08-29.

---

## Przebieg 2026-08-29 — Z2, ekran `Płynność` (`testy/test_ekran_plynnosc.py`, `interfejs/testy/wykres.test.ts`)

Kopia drzewa: `scratchpad/mutacje-z2` (poza repozytorium), `node_modules` podpięte dowiązaniem,
`__pycache__` czyszczony przed każdym przebiegiem.

Kontrola przed mutacjami: **49 passed** (pytest) · **14 passed** (vitest).

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **P1** | `napisy.ts`: etykieta wielkiej liczby `Najniżej — X` → `Stan na X` | — **przed poprawką: ŻADEN** | **ZIELONY — strażnik-atrapa** |
| **P1′** | ta sama mutacja po naprawie | `test_kazda_fraza_z_ramki_JEST_na_ekranie` · `test_etykieta_NAJNIZEJ_stoi_przy_wielkiej_liczbie` | **czerwony** |
| **P2** | `page.tsx`: kwota `−210,67 zł` wpisana wprost w komponent | `test_ekran_NIE_MA_wpisanej_recznie_kwoty` | **czerwony** |
| **P3** | `dane/plynnosc.ts`: saldo przeniesione na **pierwszą** pozycję dnia 25 IX | — **przed poprawką: ŻADEN** | **ZIELONY — strażnik-atrapa** |
| **P3′** | ta sama mutacja po naprawie | `test_saldo_bite_RAZ_NA_DZIEN` | **czerwony** |
| **P4** | `page.tsx`: prognoza rysowana linią ciągłą (`strokeDasharray` zdjęty) | `test_prognoza_JEST_kreska_przerywana` | **czerwony** |
| **P5** | `style.module.css`: podwójna linia zamknięcia rysowana liniaturą zamiast atramentem cichym | `test_podwojna_linia_jest_ATRAMENTEM_nie_liniatura` | **czerwony** |
| **P6** | `page.tsx`: ikona dołożona do bloku werdyktu | `test_werdykt_NIE_DOSTAJE_ikony` | **czerwony** |
| **P7** | `lib/wykres.ts`: górny margines rysunku `10` → `9` px | `wykres.test.ts > sciezka prognozy odtwarza sie z ramki…` · `> linia zera stoi tam, gdzie w ramce` | **czerwony** |
| **P8** | `style.module.css`: barwa szesnastkowa zamiast zmiennej palety | `test_styl_NIE_MA_wpisanej_recznie_barwy` | **czerwony** |
| **P9** | `napisy.ts`: wraca zdanie „prognoza ich NIE dolicza" | `test_ekran_NIE_KLAMIE_o_ratach_spoza_planu` | **czerwony** |

Kontrola po cofnięciu wszystkich mutacji: **49 passed** · **14 passed**.

### Co znalazła P1 — strażnik pilnował słowa, nie miejsca

`test_kazda_fraza_z_ramki_JEST_na_ekranie` szukał słowa `Najniżej` **w całym nośniku brzmień**.
Obok używanego klucza `najnizej` stał wtedy drugi, nieużywany (`najnizejBezZejscia`) z tym samym
zdaniem — więc podmiana **działającej** etykiety niczego nie czerwieniła: słowo nadal gdzieś było.

Gdyby to zostało: etykieta `NAJNIŻEJ — 25 WRZEŚNIA` mogłaby zniknąć przy zielonej suicie,
a bramka odwzorowania **też by tego nie złapała** — sam napis to ok. 600 pikseli atramentu,
czyli 0,05% obrazu przy progu 2%.

**Domknięcie:** drugi, nieużywany klucz skasowany (był drugim nośnikiem jednego zdania), a test
trafia teraz w **konkretny klucz** wyrażeniem `najnizej:\s*\([^)]*\)\s*=>\s*` i sprawdza treść
szablonu, nie obecność słowa w pliku.

### Co znalazła P3 — wzorzec liniowy widział pięć wierszy z sześciu

`test_saldo_bite_RAZ_NA_DZIEN` czytał księgę wyrażeniem z `[^\n]*?`, więc **pierwszy wpis, rozbity
na kilka linii, w ogóle do pomiaru nie docierał** — sprawdzenie widziało 5 wierszy z 6 i nie
wiedziało o tym. Osobno: liczyło wyłącznie „ile sald na dzień", a nie „na której pozycji dnia",
więc przeniesienie salda z ostatniej pozycji 25 IX na pierwszą przechodziło jako poprawne.

**Domknięcie:** wzorzec z `re.S`, **kontrola liczności** (`len(wiersze) == ksiega.count("dzien:") == 6`)
i osobna asercja, że saldo stoi na **ostatniej** pozycji dnia — bo konwencja księgi to saldo na
koniec dnia, a saldo pokazane w połowie dnia jest liczbą, której nikt nie potrafi sprawdzić.

### Czego ten przebieg NIE objął

Bramki odwzorowania nie mutowano — kontrola dwustronna pochodzi z Z0 i została **powtórzona**
przed użyciem narzędzia jako dowodu: `Main` wobec `Main` = **0,00%**, 1 296 000 porównanych pikseli,
2026-08-29.

---

## Przebieg 2026-08-29 — Z2b, Płynność dogania ramkę po Z3 (`test_ekran_plynnosc.py`, `interfejs/testy/karta.test.ts`)

Kopia drzewa: `scratchpad/mutacje-z2b` (poza repozytorium), `__pycache__` czyszczony przed każdym
przebiegiem. Kontrola przed mutacjami: **58 passed** (pytest) · **22 passed** (vitest).

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **R1** | `lib/ekrany.ts`: `ZNAK_SLOWNY` `"FINANSE"` → `"Doradca"` | `test_znak_slowny_MA_JEDNA_wartosc_w_kodzie_i_w_ramkach` | **czerwony** |
| **R2** | `powloka.css`: światło znaku `0.12em` → `0.16em` | `test_znak_slowny_MA_JEDNA_wartosc_w_kodzie_i_w_ramkach` | **czerwony** |
| **R3** | `style.module.css`: kotwica `28px` → `15px` | `test_kotwica_STOI_STOPIEN_WYZEJ_niz_salda_posrednie` | **czerwony** |
| **R4** | `page.tsx`: karta „Co mam zrobić" zdjęta z ekranu | `test_karta_STOI_NA_EKRANIE_miedzy_werdyktem_a_wezwaniem` | **czerwony** |
| **R5** | `karta-dzialania.ts`: warunek deficytu zawsze prawdziwy (stan dobry nieosiągalny) | `karta.test.ts > stan 2 — wszystko w porzadku…` | **czerwony** |
| **R6** | `napisy.ts`: brzmienie kosztu w stanie dobrym skrócone (rozjazd z ramką) | `karta.test.ts > stan 2 — wszystko w porzadku…` | **czerwony** |
| **R7** | `napisy.ts`: stan bez danych zaczyna podawać kwotę `0,00 zł` | `karta.test.ts > stan 3 — brak danych…` | **czerwony** |
| **R8** | `dane/plynnosc.ts`: liczba zdjęta decyzją D-55 wraca na ekran | `test_element_zdjety_decyzja_D55_NIE_WRACA` | **czerwony** |
| **R9** | `napisy.ts`: drugie działanie (nadpłata kredytu) dołożone do nośnika brzmień karty | `karta.test.ts > nosnik brzmien nie zawiera drugiego dzialania…` | **czerwony** |

Kontrola po cofnięciu wszystkich mutacji: **58 passed** · **22 passed**.

### Czym różni się ten przebieg od dwóch poprzednich

W Z1 i Z2 mutacja **znalazła atrapę** (M3, P1, P3). Tutaj żadna nie przeszła na zielono — i to jest
skutek wniosku z tamtych przebiegów, nie szczęścia. Przy każdym nowym strażniku sprawdzano najpierw,
**w co dokładnie trafia i ile rzeczy widzi**:

- `test_znak_slowny…` czyta wartość z ramek **wzorcem trafiającym w rolę** (span o wadze 700
  i wersalikach), nie w dowolne wystąpienie słowa, i ma **kontrolę liczności** — `len(trafienia) >= 30`
  oraz osobne sprawdzenie, że komplet sześciu ramek wiążących w ogóle znak słowny niesie. Bez tego
  wzorzec, który przestałby cokolwiek znajdować, meldowałby zgodność.
- `karta.test.ts` **nie porównuje z napisem przepisanym do testu**, tylko z tekstem wyciętym
  z `makiety/CoMamZrobic.dc.html` przy każdym przebiegu — bo przepisany napis byłby trzecim nośnikiem
  jednego zdania, czyli dokładnie tym, co rozjechało znak słowny. Kontrola liczności: ramka
  specyfikacji musi dać **dokładnie trzy karty** o **2, 2 i 1** akapicie.
- `test_kotwica…` sprawdza nie tylko wartości, ale i **kolejność reguł w arkuszu**. Zmierzone przy
  budowie: `.komorkaSaldaKotwicy` postawiona przed `.komorkaSalda` była nadpisywana przy tej samej
  szczegółowości, więc kotwica zostawała przy 15 px, a wiersz miał 44 px zamiast 61 px — arkusz
  wyglądał poprawnie i był bezskuteczny.

### Czego ten przebieg NIE objął

Bramki odwzorowania nie mutowano; użyto **kontroli dwustronnej** przed powołaniem się na jej wynik:
`Main` wobec `Main` = **0,00%**, a **ekran Płynności wobec cudzej ramki (`Ksiegowanie`) = 24,91%**.
Drugi przebieg jest tu ważniejszy od pierwszego: wynik `0,00%` dla ekranu wobec własnej ramki jest
na tyle nietypowy, że wymaga dowodu, iż pomiar w ogóle dociera do strony.

---

## Przebieg 2026-08-29 — Z4, przeniesienie silnika

Kopia drzewa poza repozytorium (`scratchpad/mut`), `__pycache__` czyszczony przed **każdym**
przebiegiem. Kontrola bazowa kopii przed mutacjami: **756 passed, 3 deselected** — identycznie
jak w repozytorium.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M1** | Kopia tabeli progów składki zdrowotnej wraca do `silnik/rdzen/formy.py` (`if przychod < 60000 … elif <= 300000 …`) zamiast wywołania `stawki.mnoznik_dla_przychodu` | `test_porownanie_form_liczy_zdrowotna_Z_NOSNIKA[300000]` · `test_progi_zdrowotnej_maja_JEDEN_nosnik` · `test_mnozniki_progow_maja_JEDEN_nosnik` · `test_formy_nie_ma_ANI_JEDNEGO_literalu_stawki` | **czerwony** |
| **M2** | `prezentacja.MINUS` wraca na dywiz ASCII (`"−"` → `"-"`) | `test_minus_przy_kwocie_to_U2212_a_NIE_dywiz_ASCII` · `test_stala_MINUS_jest_ZAPISANA_ucieczka_a_nie_wklejona` · `test_zloty_daje_polskie_separatory_i_jednostke` | **czerwony** |
| **M3** | `stawki.do_groszy` znowu liczy samo (własne `quantize` z `ROUND_HALF_UP`) zamiast wołać `pieniadz.do_groszy` | `test_zaokraglenie_ma_JEDEN_nosnik_i_jest_nim_pieniadz` · `test_kwota_nie_jest_liczona_wlasnym_quantize_poza_pieniadzem` | **czerwony** |

Kontrola po cofnięciu każdej mutacji z osobna: **756 passed, 3 deselected**.

### M1 — dlaczego akurat 300 000 zł i dlaczego to jest sedno tego przebiegu

Strażnik behawioralny `test_porownanie_form_liczy_zdrowotna_Z_NOSNIKA` jest sparametryzowany
ośmioma wartościami. Mutacja M1 czerwieni **dokładnie jedną z ośmiu** — `[300000]`:

```
E   assert Decimal('9967') == Decimal('17940')
```

To nie jest ciekawostka o pokryciu. **Dokładnie ta różnica siedziała w kodzie poprzednika**:
kopia porównywała nieostro (`elif przychod <= Decimal("300000")`), nośnik ostro
(`if przychod < prog.limit_gorny`), więc przy przychodzie równym 300 000 zł kopia dawała mnożnik
1,00, a nośnik 1,80. W kwotach: **1 495,04 zł wobec 830,58 zł miesięcznie — 664,46 zł na miesiąc,
7 973,52 zł na rok**, na korzyść ryczałtu, czyli w stronę, w którą porównanie form ma **nie** być
stronnicze.

**591 przeniesionych testów przechodziło i przed naprawą, i po niej.** Żaden nie dotykał tej
wartości. Wada została znaleziona **porównaniem kopii**, nie testem — i to jest powód, dla którego
strażnik pyta o granice przedziałów, a nie o wartości „typowe".

Test `test_granica_300000_jest_MIEJSCEM_w_ktorym_kopie_sie_rozjechaly` stoi obok jako kontrola
drugiego rodzaju: pilnuje, żeby 300 000 zł **nadal rozdzielało dwa progi**. Gdyby przepis to
zmienił, test wyżej dalej byłby zielony, ale przestałby cokolwiek znaczyć — mierzyłby granicę,
której nie ma.

### M3 — mutacja, która znalazła trzy kolejne kopie

Strażnik `test_kwota_nie_jest_liczona_wlasnym_quantize_poza_pieniadzem` **zaczerwienił się
natychmiast po napisaniu**, zanim doszło do jakiejkolwiek mutacji, i wskazał trzy pliki:
`doradca.py`, `import_arkusza.py`, `narzedzia.py`. Każdy z nich wołał `quantize(Decimal("0.01"))`
**bez podania trybu**, czyli zaokrąglał **bankiersko**, a konwencją projektu jest `ROUND_HALF_UP`:

```
     1.005  domyslne(HALF_EVEN)=1.00  regula projektu(HALF_UP)=1.01  ROZJAZD
     0.125  domyslne(HALF_EVEN)=0.12  regula projektu(HALF_UP)=0.13  ROZJAZD
  1305.045  domyslne(HALF_EVEN)=1305.04  regula projektu(HALF_UP)=1305.05  ROZJAZD
```

Sam `import_arkusza.py` niósł w innym miejscu komentarz ostrzegający dokładnie przed tym błędem —
i w tym samym pliku, dwadzieścia linii niżej, popełniał go w kluczu odsiewania duplikatów.
Wszystkie trzy przepisano na `stawki.do_groszy`.

### Czego ten przebieg NIE objął

- **Nie mutowano `magazyn.py`** (2101 linii, jedyny moduł dotykający SQLite). Przeniesiony bez
  zmian merytorycznych; jedyna zmiana to poziom katalogu w `SCIEZKA_DOMYSLNA`, którą pilnuje
  `test_konfiguracja.py::test_domyslna_sciezka_wskazuje_katalog_projektu` i strażnik ścieżki
  z `conftest.py`.
- **Nie mutowano strażnika ścieżki bazy produkcyjnej.** Powołuję się na niego jako na bramkę,
  więc pozycja jest **niepotwierdzona mutacją** — etykieta jawna, nie przeoczenie. Przeniesiony
  test `test_sciezka_bazy.py` niesie własną kontrolę liczności
  (`test_straznik_ISTNIEJE_a_nie_tylko_powinien`) i kontrolę dwustronną
  (`test_straznik_PRZEPUSZCZA_sciezke_spoza_produkcji`), co jest słabsze niż mutacja.

---

## Przebieg 2026-08-29 — Z5, kontrakt po obu stronach granicy

Kopia drzewa poza repozytorium (`scratchpad/mut5`), `__pycache__` czyszczony przed **każdym**
przebiegiem. Kontrola bazowa kopii: **807 passed, 3 deselected** — identycznie jak w repozytorium.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M4** | Zmiana nazwy pola w `silnik/kontrakt.py`: `saldoPoDniu` → `saldoDnia` | `test_nazwy_pol_sie_ZGADZAJA[PozycjaKsiegi]` · `test_OPCJONALNOSC_pol_sie_zgadza[PozycjaKsiegi]` · `test_TE_SAME_pola_sa_kwotami[PozycjaKsiegi]` · `test_saldo_bite_RAZ_NA_DZIEN` · `test_saldo_raz_na_dzien_NIE_MODYFIKUJE_wejscia` · `test_ODPOWIEDZ_zlozona_z_kontraktu_przechodzi_granice_bez_ani_jednej_liczby` | **czerwony** |
| **M5** | `api/kwoty.py`: `kwota()` zwraca `float(...)` zamiast `str(...)` | `test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ` · `test_ODPOWIEDZ_zlozona_z_kontraktu_przechodzi_granice_bez_ani_jednej_liczby` | **czerwony** |
| **M6** | `silnik/rdzen/magazyn.py`: `sciezka_bazy()` przestaje wołać `STRAZNICY_SCIEZKI` | `test_pod_pytestem_produkcyjna_sciezka_jest_BLEDEM` | **czerwony** |

Kontrola po cofnięciu każdej mutacji z osobna: **807 passed, 3 deselected**.

### M4 — komunikat mówi też, w którą stronę naprawiać

```
E  AssertionError: PozycjaKsiegi: tylko we wzorcu ['saldoPoDniu'];
   tylko w Pythonie ['saldoDnia']. Wzorcem jest `kontrakt.ts` — poprawia się Python.
```

Kierunek zgodności stoi **w treści błędu**, nie tylko w nagłówku pliku. Strażnik, który mówi
„niezgodność", zostawia wykonawcy wybór, którą stronę zmienić — a ten wybór jest już podjęty:
oba ekrany są zbudowane wobec `kontrakt.ts` i przechodzą bramkę odwzorowania.

### M5 — dowód, że obchód idzie w głąb, a nie po wierzchu

```
E  AssertionError: liczba zmiennoprzecinkowa w odpowiedzi:
   ['$.saldoMinimalne', '$.ksiega[0].saldoPoDniu', '$.ksiega[1].kwota',
    '$.ksiega[1].saldoPoDniu', '$.ksiega[2].kwota', '$.wykres[0].saldo']
```

**Pięć z sześciu znalezisk leży poniżej pierwszego poziomu**, w listach obiektów. Obchód sprawdzający
tylko wierzch znalazłby jedno (`$.saldoMinimalne`) i zameldowałby, że reszta jest w porządku —
a wszystkie kwoty tego projektu siedzą właśnie w `ksiega` i `wykres`.

Przebieg końcowy odwiedza **21 liści** dla realistycznej odpowiedzi (cztery pola wierzchnie,
trzy pozycje księgi po pięć pól, jeden punkt wykresu po dwa) i ta liczba jest **sprawdzana
asercją**, nie tylko raportowana. Bez niej mutacja polegająca na tym, że obchód nigdzie nie
dociera, przeszłaby na zielono: pusta lista ścieżek wygląda identycznie jak brak wady.

### M6 — domknięcie długu zgłoszonego w Z4

W raporcie z Z4 zgłosiłem: *„strażnik ścieżki bazy produkcyjnej jest niepotwierdzony mutacją,
a powołuję się na niego jako na bramkę"*. **Dług domknięty — strażnik jest potwierdzony.**

Mutacja celowo trafia w **kod produkcyjny** (`magazyn.sciezka_bazy` przestaje wołać listę
strażników), nie w `conftest.py`. Mutacja w `conftest.py` dowiodłaby tylko tego, że test czyta
konfigurację testów; ta dowodzi, że **mechanizm w silniku** naprawdę stoi między testem a bazą
z realnymi finansami. Komunikat: `Failed: DID NOT RAISE BladMagazynu`.

### Czego ten przebieg NIE objął

- **Nie mutowano strony TypeScriptu.** `interfejs/lib/kontrakt.ts` jest wzorcem i cudzą własnością
  (Z1/Z2); czytam go, nie piszę do niego. Skutek: **nie wykazałem mutacją**, że strażnik czerwieni
  się na zmianie po stronie wzorca — wnioskuję to z symetrii porównania zbiorów, co jest słabsze
  niż pomiar. Etykieta jawna: **ta połowa strażnika jest niepotwierdzona**.
- **Rozjazd separatora tysięcy nie jest wadą do naprawy w tym zadaniu, tylko długiem przypiętym.**
  `test_dwa_nosniki_formatowania_kwoty_sa_PRZYPIETE` nie sprawdza zgodności — pilnuje, żeby
  **znana** różnica (Python U+00A0, TypeScript U+0020) nie zmieniła się bez decyzji. Ramki niosą
  U+0020, więc odstaje strona Pythona.

---

## Przebieg 2026-08-29 — Z6, sześć tras pod dwa ekrany (`testy/test_trasy_dwa_ekrany.py`, `testy/test_trasy_bez_rachunku.py`)

Kopia drzewa poza repozytorium (`scratchpad/mut-z6`), `__pycache__` czyszczony **przed każdym**
przebiegiem, po jednej mutacji na przebieg. Kontrola bazowa kopii: **849 passed, 3 deselected** —
identycznie jak w repozytorium (przed dołożeniem M-Z6-8: 849). Kontrola po cofnięciu wszystkich ośmiu: **850 passed,
3 deselected**, a `diff -rq` katalogów `api/` i `silnik/` wobec repozytorium: bez różnic.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-Z6-1** | `api/kwoty.py`: `kwota()` zwraca `float(...)` zamiast `str(...)` | `test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej` (+ 18 dalszych, w tym cały `test_trasy_dwa_ekrany.py` i dwa z `test_kontrakt_dwa_nosniki.py`) | **czerwony** |
| **M-Z6-2** | `api/trasy_plynnosc.py`: `APIRouter(default_response_class=…)` → `APIRouter()` | `test_KAZDY_router_ma_klase_odpowiedzi_ODMAWIAJACA_liczb` | **czerwony** |
| **M-Z6-3** | `silnik/ekran_ksiegowanie.py`: `rozstrzygnij_kwote` przestaje zwracać stan pytania — minus schodzi po cichu | `test_kwota_UJEMNA_zwraca_PYTANIE_a_nie_blad_i_NIC_nie_zapisuje` | **czerwony** |
| **M-Z6-4** | `silnik/ekran_plynnosc.py`: `ksiega=kontrakt.zbij_saldo_raz_na_dzien(ksiega)` → `tuple(ksiega)` | `test_ksiega_bije_saldo_RAZ_NA_DZIEN` | **czerwony** |
| **M-Z6-5** | `silnik/ekran_ksiegowanie.py`: `KATEGORIE_POZA_EKRANEM = ()` — kategoria kosztu firmowego wraca na ekran | `test_kategoria_kosztu_firmowego_NIE_STOI_na_tym_ekranie` · `test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej` | **czerwony** |
| **M-Z6-6** | `silnik/ekran_ksiegowanie.py`: czwarty wiersz podglądu („Wolne środki") nie jest dokładany | `test_podglad_ma_CZTERY_wiersze_a_czwarty_mowi_co_sie_NIE_ruszylo` · `test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej` | **czerwony** |
| **M-Z6-8** | `silnik/rdzen/podatki.py`: `rezerwa_z_bazy` przestaje podawać formę z bazy i liczy zawsze ryczałtem 8,5% | `test_FORMA_OPODATKOWANIA_dojezdza_az_do_odpowiedzi_HTTP` · `test_zbieracz_PODAJE_silnikowi_takze_FORME_z_bazy` · `test_stan_roku_ZMIENIA_prognoze_a_nie_tylko_do_niej_wchodzi` (+ 3 dalsze z `test_trasy_dwa_ekrany.py`) | **czerwony** |
| **M-Z6-7** | `api/trasy_plynnosc.py`: trasa mnoży `saldoMinimalne` przez 2 przed zwróceniem | `test_cialo_trasy_NIE_LICZY_niczego[trasy_plynnosc.py::plynnosc]` · `test_cialo_trasy_to_JEDNO_zdanie_return[trasy_plynnosc.py::plynnosc]` | **czerwony** |

### M-Z6-1 i M-Z6-2 — dwie mutacje, bo jedna nie wystarczała

To jest najważniejsza pozycja tego przebiegu i wyszła dopiero z pomiaru, nie z projektu.

Mutacja M-Z6-1 zaczerwieniła 19 testów, ale **nie tak, jak zakładałem**. Odpowiedź z liczbą
zmiennoprzecinkową nigdy nie dojechała do przeglądarki: `OdpowiedzJSON` odmówiła jej wypuszczenia
i trasy zwróciły kod 500. Strażnik `test_ZADNA_z_szesciu_tras…` zaczerwienił się więc **na kodzie
odpowiedzi, nie na liczbie w treści**. Sprawdzenie „w odpowiedzi nie ma liczby zmiennoprzecinkowej"
nie ma jak paść inaczej, bo **mierzy to samo, co bramka, którą sprawdza** — a bramka stoi wcześniej.

Wniosek: ten strażnik nie dowodzi, że liczby nie wychodzą. Dowodzi, że **sześć tras naprawdę
zostało wywołanych i wszystkie odpowiedziały kodem 200**. Rzeczą, która faktycznie broni granicy,
jest klasa odpowiedzi ustawiona **w konstruktorze `APIRouter`** — i to ona dostała własnego
strażnika oraz własną mutację (M-Z6-2). Dopiero M-Z6-2 pada pojedynczo, na mechanizmie:

```
E  AssertionError: trasy_plynnosc: klasa odpowiedzi to
   <fastapi.datastructures.DefaultPlaceholder object at 0x10d048e50>,
   a nie OdpowiedzJSON — liczby zmiennoprzecinkowe wyjda z 200
```

To nie jest szczegół konfiguracji. U poprzednika zmierzono (FastAPI 0.141), że klasa odpowiedzi
przekazana do `include_router` **nie dociera do trasy** — więc router bez niej wygląda dokładnie
tak samo jak router z nią, aż do chwili, w której grosze zaczynają znikać przy kodzie 200.

### M-Z6-5 i M-Z6-6 — przypięta liczba liści działa jako strażnik kształtu

Obie mutacje zmieniły **kształt** odpowiedzi (o jedną kategorię więcej, o jeden wiersz mniej)
i obie zaczerwieniły także `test_ZADNA_z_szesciu_tras…` — nie przez liczbę zmiennoprzecinkową,
tylko przez przypiętą liczbę odwiedzonych liści:

```
E  AssertionError: liczba lisci odpowiedzi sie zmienila:
   {'GET /api/ksiegowanie': 76, 'POST /api/wpisy': 86,
    'DELETE /api/wpisy/{id}': 80, …} wobec
   {'GET /api/ksiegowanie': 73, 'POST /api/wpisy': 83,
    'DELETE /api/wpisy/{id}': 77, …}
```

Licznik liści powstał jako **kontrola liczności** obchodu („sprawdzenie, do którego nic nie
dociera, melduje sukces") i przy okazji okazał się strażnikiem kształtu odpowiedzi. Zmiana
którejkolwiek z sześciu liczb jest sygnałem do sprawdzenia, nie pozycją do podbicia.

### M-Z6-8 — jedyna mutacja, która sięgnęła poza warstwę sieciową

Ryczałt jest w tym projekcie **wadą, nie opcją domyślną**, i to jest zmierzony mechanizm awarii,
nie hipoteza: rachunek liczył ryczałtem komuś, kto jest na skali, i robił to wiarygodnie.
`testy/test_forma_bez_domyslnej.py` pilnuje, że **pominięcie** formy jest błędem wywołania —
ale nie odpowiada na pytanie o poziom wyżej: czy forma zapisana w bazie zmienia **liczbę
wychodzącą z trasy**. Ta mutacja odpowiada: zmienia. Skala i ryczałt na tych samych danych dają
`2986.44` wobec innej wartości, a gdyby były równe, żaden inny test tego pliku by tego nie
zauważył.

### Czego ten przebieg NIE objął

- **Nie mutowano `zdanie_werdyktu` ani `najnizszy_punkt`.** Oba mają testy
  (`test_zdanie_werdyktu_nazywa_PRZYCZYNE_nie_tylko_fakt`), ale **żaden z nich nie został
  potwierdzony mutacją** — etykieta jawna: ta część jest **niepotwierdzona**, dokładnie w rozumieniu
  §3.8. Kandydat na kolejny przebieg: `_co_wychodzi_tego_dnia` zwracające pusty napis.
- **Nie mutowano strony TypeScriptu** — `interfejs/` jest cudzą własnością (Z1/Z2); czytam go,
  nie piszę do niego.
- **Nie ma strażnika behawioralnego** — żaden z tych testów nie mówi, że liczba **na ekranie**
  równa się liczbie z silnika. Ta luka zostaje otwarta do zadania Z7, którego bramka brzmi
  „prognoza po wpisie jest inna niż przed".

---

## Przebieg 2026-08-29 — Z7 (podpięcie): strażnicy warstwy danych i strażnik ekran-wobec-silnika

**Kopia drzewa poza repozytorium:** `scratchpad/mut-z7` (`rsync` bez `.git`, `.venv`, `.next`,
`__pycache__`), własne `node_modules` skopiowane, nie dowiązane — Turbopack odmawia pracy
z dowiązaniem wychodzącym poza korzeń projektu. `__pycache__` czyszczone **przed każdym**
przebiegiem. Serwer kopii na porcie **3100**, żeby nie mieszać się z przebiegiem odbiorczym
na 3000.

Kontrola przed mutacjami: **859 passed, 3 deselected** (Python, w kopii) ·
strażnik ekran-wobec-silnika **kod wyjścia 0, 15 porównanych liczb**.

| # | Mutacja | Który test / sprawdzenie padło | Wynik |
|---|---|---|---|
| **M-Z7-1** | `lib/dane/plynnosc.ts`: wraca stała `const SALDO_STARTOWE: Kwota = "9601.03"` | `test_warstwa_danych_NIE_MA_ANI_JEDNEJ_wpisanej_kwoty` | **czerwony** |
| **M-Z7-1b** | wszystkie pliki `lib/dane/*.ts` znikają (kontrola liczności) | `test_skan_NAPRAWDE_cokolwiek_zobaczyl` · `test_warstwa_danych_WOLA_TRASY_zamiast_niesc_stale` | **czerwony** |
| **M-Z7-1c** | `warstwa-sieciowa.ts`: `cache: "no-store"` → `cache: "force-cache"` | — **przed poprawką: ŻADEN (4 passed)** | **ZIELONY — atrapa** |
| **M-Z7-1c′** | ta sama mutacja po zdjęciu komentarzy w strażniku | `test_warstwa_danych_WOLA_TRASY_zamiast_niesc_stale` | **czerwony** |
| **M-Z7-1d** | `plynnosc.ts` woła `/api/prognoza` zamiast `/api/plynnosc` | `test_warstwa_danych_WOLA_TRASY_zamiast_niesc_stale` | **czerwony** |
| **M-Z7-2** | `app/page.tsx`: saldo rysowane znakiem `"ujemna"` zamiast `"neutralna"` | strażnik ekran-wobec-silnika, 7× `KSIEGA[i].saldo`, **kod wyjścia 1** | **czerwony** |
| **M-Z7-3** | `app/page.tsx`: `ksiega.slice(0, 3)` — ekran rysuje trzy pierwsze pozycje | strażnik ekran-wobec-silnika, `LICZNOSC_WIERSZY: silnik 7, ekran 3` | **czerwony** |
| **M-Z7-4** | `ekran_ksiegowanie._alfabetycznie` → `(nazwa, nazwa)` (porządek po surowych znakach) | `test_pasmo_ma_PIETNASCIE_kategorii_w_kolejnosci_Z_REGULY_SILNIKA` | **czerwony** |
| **M-Z7-5** | `app/page.tsx`: ekran przestaje rysować `w.dopisek` przy wierszu otwarcia | `test_kotwica_NIESIE_WIEK_odczytu` | **czerwony** |
| **M-Z7-6** | `app/page.tsx`: kolumna salda liczy regułę „raz na dzień" u siebie (`przedDalszym`) | `test_ekran_NIE_POWTARZA_reguly_saldo_raz_na_dzien` | **czerwony** |
| **M-Z7-7** | `app/page.tsx`: wiersz zamknięcia bierze `DANE.wykres[0].saldo` zamiast `saldoMinimalne` | strażnik ekran-wobec-silnika, `WIERSZ_ZAMKNIECIA: silnik „7 485,98 zł", ekran „9 601,03 zł"` | **czerwony** |

Kontrola po cofnięciu wszystkich mutacji: **859 passed, 3 deselected** · strażnik
ekran-wobec-silnika **kod wyjścia 0** · `diff -r` kopii z repozytorium: bez różnic poza
dziennikiem sesji.

### Co znalazła M-Z7-1c — i dlaczego to najważniejsza pozycja tej tabeli

Strażnik miał pilnować, że warstwa sieciowa **nie buforuje** odpowiedzi. Bufor `fetch`
w komponencie serwerowym Next.js oddałby drugie zapytanie z pamięci, więc bramka całej nocy —
„prognoza po wpisie jest inna niż przed" — mierzyłaby wtedy pamięć przeglądarki, nie silnik.
To jest awaria, która **melduje sukces**: ekran wygląda poprawnie i pokazuje stan sprzed wpisu.

Mutacja przeszła **na zielono**, bo strażnik czytał plik **razem z komentarzami**, a nagłówek
tego samego pliku cytuje `cache: "no-store"` w zdaniu tłumaczącym, po co bufor jest wyłączony.
Sprawdzenie „ta fraza JEST w pliku" trafiało w komentarz o frazie, nie we frazę.

To **trzecie** trafienie tego samego wzorca w tym projekcie (M3 z Z1 — `autoFocus` w komentarzu;
`pomocnicze.bez_komentarzy` powstało właśnie po nim) i drugie, w którym autor strażnika sam
napisał komentarz, który go unieważnił. Wykryła to mutacja, nie czytanie kodu.

### Czego ten przebieg NIE objął — i co przez to zostaje niepilnowane

- **Strażnik ekran-wobec-silnika dzieli z ekranem nośnik formatowania** (`lib/kwota.ts`).
  Wada **wewnątrz** `sformatujKwote` — na przykład zgubiony grosz — zmieni obie strony
  porównania naraz i strażnik jej **nie zobaczy**. To jest granica świadoma, nie przeoczenie:
  alternatywą byłaby druga kopia reguły formatowania w narzędziu, czyli dokładnie ten drugi
  nośnik, przed którym broni §3.2. Tę połowę pilnuje `interfejs/testy/kwota.test.ts`, który
  porównuje wynik ze znakami **wyciętymi z ramki**, a nie z kodu.
- **Strażnik czyta wyłącznie ekran Płynności.** Liczby ekranu Księgowania („Co ruszy ten wpis",
  „Ostatnie wpisy") **nie są** porównywane z odpowiedzią trasy — etykieta jawna: ta część jest
  **niepotwierdzona**. Kandydat na kolejny przebieg: te same cztery wiersze karty wobec
  `POST /api/wpisy/podglad`.
- **Nie mutowano `silnik/` poza `_alfabetycznie`** — silnik jest w tym zadaniu cudzą własnością
  (Z4/Z5/Z6); czytam go, nie piszę do niego. Jedyna mutacja tam była **odwracalna i wykonana
  w kopii**, żeby pokazać, że przerysowany strażnik pasma naprawdę mierzy regułę, a nie stałą.

---

## Przebieg 2026-08-29 — Z7b, prognoza czyta wpisy (D-20, D-61)

Kopia drzewa poza repozytorium (`scratchpad/mut-z7b`), `__pycache__` czyszczony przed **każdym**
przebiegiem. Kontrola bazowa kopii: **880 passed, 3 deselected** — identycznie jak w repozytorium.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-Z7b-1** | **D-20 zdjęte** — `podziel_os` przestaje filtrować plan po dacie (`p.dzien > dzis` → `True`) | `test_plan_na_dzien_MINIONY_NIE_obciaza_osi` · `test_pozycja_BEZ_dnia_platnosci_ma_dzien_DOMNIEMANY_i_liczbe` | **czerwony** |
| **M-Z7b-2** | **D-61 zdjęte** — budżet konsumpcji zawsze zerowy, wpis nie zjada pozycji planu | `test_PODWOJNE_LICZENIE_nie_wystepuje_604_06_nie_pada` · `test_PRZYPADEK_1_wpis_MIESCI_SIE_w_planie…` · `test_PRZYPADEK_2_wpis_PRZEKRACZA_plan…` | **czerwony** |
| **M-Z7b-3** | **Wpisy w ogóle nie wchodzą na oś** (stan sprzed Z7b) | sześć testów `test_prognoza_czyta_wpisy.py`, w tym obie bramki krok 1.2 | **czerwony** |
| **M-Z7b-4** | Daniny i przychód JDG wchodzą na oś **drugi raz** (zdjęte odsianie kategorii) | `test_wpisy_danin_i_przychodu_JDG_NIE_wchodza_na_os_dwa_razy[Podatki i ZUS]` · `[Wynagrodzenie]` | **czerwony** |
| **M-Z7b-5** | Klucz konsumpcji bez typu — przychód konsumuje plan wydatku | `test_wpis_PRZYCHODOWY_nie_konsumuje_planu_WYDATKU` | **czerwony** |
| **M-Z7b-6** | `liczbaPozycjiCoMnieCzeka` wraca na `len(pozycje)` — zero zamiast „nie wiem" | `test_przy_ODMOWIE_prognozy_liczba_pozycji_to_NIE_WIEM_a_nie_zero` | **czerwony** |
| **M-Z7b-7** | `DaneKsiegowania.ostatnieSprawdzenie` zawsze `None` — ekran znowu nie wie | `test_OBA_ekrany_mowia_o_strazniku_DOKLADNIE_to_samo` | **czerwony** |

Kontrola po cofnięciu wszystkich siedmiu: **880 passed, 3 deselected**.

### M-Z7b-2 — mutacja, która trafia w liczbę wymienioną w PRD po nazwisku

```
E  AssertionError: PODWOJNE LICZENIE: wpis nie skonsumowal pozycji planu
E  assert Decimal('604.06') != Decimal('604.06')
```

**604,06 zł** to dokładnie ta liczba, którą PRD przewidziało jako skutek braku D-61:
274,06 zł (6 X) plus 330,00 zł (20 X) za prąd w jednym miesiącu. Strażnik nie pyta „czy suma jest
sensowna" — pyta o **tę** wartość. Test ogólny („suma nie rośnie") przeszedłby także wtedy, gdyby
konsumpcja działała w złą stronę.

### M-Z7b-1 — dlaczego czerwieni się też cudzy test

Drugim czerwonym jest `test_pozycja_BEZ_dnia_platnosci_ma_dzien_DOMNIEMANY_i_liczbe` z pliku
sprzed Z7b — bo licznik pozycji domniemanych spadł tam z 12 na 11 dokładnie z powodu D-20.
To jest **pożądane sprzężenie**: reguła podziału osi ma widoczny skutek poza własnym plikiem
testowym, więc jej usunięcie nie da się przemilczeć zmianą jednego testu.

### M-Z7b-3 — pomiar tego, ile plasterek był wart przed tą zmianą

Mutacja przywraca stan sprzed Z7b (wpisy nie docierają na oś) i czerwieni **sześć** testów, w tym
obie bramki z kroku 1.2 planu wykonawczego. Przed Z7b te sześć testów nie istniało, a suita była
zielona — dokładnie dlatego, że nikt nie pytał o rzecz, dla której cała ścieżka „wpisz wydatek
i zobacz skutek" została zbudowana.

### Czego ten przebieg NIE objął

- **Nie mutowano strony TypeScriptu** (`kontrakt.ts`, `napisy.ts`). Zmiany tam są sprawdzane przez
  `tsc --noEmit` i przez `test_kontrakt_dwa_nosniki`, ale **nie przez mutację** — etykieta jawna.
- **Nie mutowano `zbij_saldo_raz_na_dzien`** — ma własne mutacje z przebiegu Z5.

---

## Przebieg 2026-08-29 — Z7c: wzorcowy zestaw danych, zamek zapisu, stopka obu ekranów

**Gdzie wykonano.** Kopia drzewa poza repozytorium:
`scratchpad/mut-z7c/{interfejs,makiety}`, z własnym `node_modules` (sklonowanym, nie
dowiązanym — Turbopack odmawia startu na dowiązaniu wychodzącym poza korzeń projektu)
i własnym serwerem `next dev` na porcie **3001**. Baza odbiorcza: kopia
`scratchpad/z7c.db` (204 wpisy, 46 pozycji planu, jeden wiersz `przebiegi_straznika`).

**Kontrola przed mutacjami:** `vitest run` → **37 passed**;
`straznik-ekran-wobec-silnika` → kod 0; `straznik-podwojne-klikniecie` → kod 0.

| # | Mutacja | Który test / strażnik padł | Wynik |
|---|---|---|---|
| **M-Z7c-1** | `NAPISY_PLYNNOSCI.coMnieCzeka` traktuje `null` jak zero (`${pozycji ?? 0} pozycji`) | `null czyta się jako NIE POLICZYŁEM, nigdy jako zero` · `oba stany dają DWA RÓŻNE zdania — bez tego rozróżnienie jest na papierze` | **czerwony** (2 failed / 37) |
| **M-Z7c-2** | jedno saldo wzorca rozjeżdża się z ramką (`9601.03` → `9601.30`) | `wzorzec Main niesie DOKŁADNIE kwoty ramki, w kolejności rysowania` | **czerwony** (1 failed / 37) |
| **M-Z7c-3** | `ZNACZNIK_WZORCA` przestaje stać w ramkach (skrócone brzmienie) | `znacznik wzorca stoi w ramkach i w każdym zestawie` | **czerwony** (1 failed / 37) |
| **M-Z7c-4** | `sformatujKwote` znowu zdejmuje tylko minus (`kwota.replace("-", "")`) | `wiodący plus jest ZDEJMOWANY, nie doklejany drugi raz` · `minus typograficzny wraca z tej funkcji taki sam, jak z niej wyszedł` · `para znakKwoty + sformatujKwote czyta ten sam zbiór zapisów` · `wzorzec Main-Dobrze niesie DOKŁADNIE kwoty ramki, w kolejności rysowania` | **czerwony** (4 failed / 37) |
| **M-Z7c-5** | zamek zapisu wraca na stan Reacta (`if (wLocie)` zamiast `if (zamek.current)`) | `narzedzia/straznik-podwojne-klikniecie.mjs` → **kod 1**: `3 kliknięcia dały 3 wpisy`, `Żądań POST /api/wpisy: 3`, licznik `0 → 3` | **czerwony** |
| **M-Z7c-6** | stopka Księgowania wraca na `straznik={null}` | `narzedzia/straznik-ekran-wobec-silnika.mjs` → **kod 1**: `STOPKA[KSIEGOWANIE]` i `STOPKA[DWA EKRANY]` | **czerwony** |

Kontrola po cofnięciu wszystkich sześciu: `vitest run` → **37 passed**;
`straznik-ekran-wobec-silnika` → **kod 0**; `straznik-podwojne-klikniecie` → **kod 0**
(`przyrost 1`).

### M-Z7c-5 — mutacja, która pokazała wadę ISTNIEJĄCĄ, nie wprowadzoną

Ta mutacja nie jest wymysłem na potrzeby dowodu: **jest dokładnym stanem gałęzi sprzed
tego zadania**. Pierwszy pomiar tej nocy poszedł na kod z `HEAD` (`3ee8bd0`) i dał
`3 kliknięcia → 3 żądania → 3 wpisy`, przy przycisku, który po tych kliknięciach nadal
miał `disabled === false`. Blokada opisana w nagłówku pliku jako „jedyna dzisiaj obrona
przed podwójnym wydatkiem" **nie broniła nic**: stan Reacta dociera do funkcji obsługi
dopiero przy następnym rysowaniu, a trzy `.click()` w jednym zadaniu przeglądarki biegną
przed nim. D-64 był spełniony na papierze i niespełniony w przeglądarce.

**Dlaczego zwykłe dwa kliknięcia myszą tego nie łapią:** Playwright oddaje między nimi
sterowanie pętli zdarzeń, React zdąży przerysować przycisk i pomiar mierzy wtedy atrybut
`disabled`, a nie zamek. Strażnik, który klika „po ludzku", byłby zielony na obu wersjach.

### M-Z7c-6 — i dowód, że bramka pikselowa NIE jest tu strażnikiem

Tę samą mutację (`straznik={null}`) puszczono także przez bramkę odwzorowania na
wzorcowym zestawie danych. Wynik: **0,29% przy progu 2,00% — bramka PRZESZŁA.**
Zdanie stopki zajmuje kilka tysięcy pikseli na półtora miliona, więc pomiar wyglądu nie
odróżnia ekranu, który wie, od ekranu, który zmyśla „nie wiem". Regułę D-64 pilnuje
`straznik-ekran-wobec-silnika`, nie `porownaj-z-makieta`.

Osobno: przy włączonym `--wzorzec` ta sama mutacja kończy się **kodem 2** zamiast 1 —
bo znacznikiem obecności wzorca jest właśnie zdanie stopki. Sygnał jest prawdziwy
(coś jest nie tak), ale **nazywa złą przyczynę**: mówi „ekran nie stoi na wzorcu",
gdy naprawdę stoi, tylko go nie pokazuje. Nazwane wprost, żeby następny wykonawca nie
gonił nieistniejącego problemu z konfiguracją.

### Kontrola dwustronna narzędzi pomiarowych

Obie wykonane przed użyciem narzędzi jako dowodu:

| Kontrola | Oczekiwane | Zmierzone |
|---|---|---|
| `porownaj-z-makieta.mjs Main Main` (ramka wobec siebie) | 0,00% | **0,00%** |
| `porownaj-z-makieta.mjs Ksiegowanie Main` (dwie różne ramki) | ≫ 2% | **24,91%** |
| `--wzorzec` przy działającym **prawdziwym** silniku | błąd pomiaru | **kod 2**, „ekran NIE stoi na wzorcowym zestawie danych" |
| `silnik-wzorcowy.mjs` po `SIGTERM` | liczba obsłużonych żądań | **3×** przy przebiegu bramki; **0× + UWAGA** przy przebiegu, w którym bramka nie wystartowała |

Ostatni wiersz zdarzył się naprawdę, nie w symulacji: jeden przebieg nocy wystartował
wzorzec i nie zdążył puścić bramki. Bez licznika po stronie wzorca ten przebieg byłby
nieodróżnialny od udanego.

### Czego ten przebieg NIE objął

- **Nie mutowano `--wzorzec` przez usunięcie sprawdzenia** — kierunek odwrotny (bramka bez
  sprawdzenia przechodzi) jest trywialny. Dowodem, że sprawdzenie działa, jest kontrola
  dwustronna wyżej: przy prawdziwym silniku bramka kończy kodem 2.
- **Nie mutowano `silnik/` ani `api/`** — poza zakresem tego zadania (zgłoszenia w opisie
  zgłoszenia zmiany, nie w kodzie).
- **Nie ma strażnika dla wiersza `Płynność` w karcie „Co ruszy ten wpis" (D-62)** — bo nie
  ma czego strzec: wiersz nie powstał. Powód w zgłoszeniu do Ethana/Maxa: podgląd nie
  niesie pozycji planu kategorii ani jej dnia, a bez nich trzy brzmienia D-62 nie mają
  skąd wziąć wielkości, której §3.5 żąda.

---

## Przebieg 2026-08-29 — D-62, wiersz „Płynność" na karcie „Co ruszy ten wpis" (`testy/test_podglad_plynnosc.py`)

Kopia drzewa poza repozytorium (`scratchpad/mut-d62`), `__pycache__` czyszczony **przed każdym**
przebiegiem, po jednej mutacji na przebieg. Kontrola bazowa kopii: **892 passed, 3 deselected**.
Kontrola po cofnięciu wszystkich trzech: **892 passed, 3 deselected**, a `diff -rq` katalogów
`silnik/` i `api/` wobec repozytorium — bez różnic.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-D62-1** | `silnik/ekran_ksiegowanie.py`: piąty wiersz („Płynność") nie jest dokładany — karta wraca do czterech | `test_podglad_ma_PIEC_wierszy_a_dwa_ostatnie_mowia_co_sie_NIE_ruszylo` · wszystkie 6 testów brzmień · wszystkie 5 przypadków `test_WIELKOSC_w_zdaniu_ROWNA_SIE_ruchowi_ktory_zobaczy_uzytkownik` · `test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej` (13 czerwonych) | **czerwony** |
| **M-D62-2** | `silnik/rdzen/prognoza_plynnosci.py`: `SkutekNaOs.roznica` bierze **kwotę wpisu** zamiast różnicy dwóch przebiegów `podziel_os` | `test_WIELKOSC_w_zdaniu_ROWNA_SIE_ruchowi_ktory_zobaczy_uzytkownik[274.06/330.00/374.06/500.00-Energia Elektryczna]` · 3 testy brzmień (7 czerwonych) | **czerwony** |
| **M-D62-3** | `silnik/ekran_ksiegowanie.py`: zdanie zawsze mówi „pozycja schodzi z osi w całości", niezależnie od reszty | `test_wpis_MIESCI_SIE_w_planie_mowi_o_dacie_i_o_RESZCIE_pozycji` | **czerwony** |

### M-D62-2 — mutacja pisana pod jedno konkretne pytanie bramki

Bramka odbioru D-62 punkt 2 brzmi: *„wielkość wzięta z innego rachunku niż ta, którą opisuje,
to wada"*. Ta mutacja **jest** tą wadą, wykonaną celowo: podmienia różnicę osi na kwotę wpisu —
liczbę, która leży w zasięgu ręki, wygląda wiarygodnie i **w jednym z pięciu przypadków jest nawet
prawdziwa**. Strażnik zapala się na czterech i milczy na piątym:

```
E  AssertionError: karta zapowiedziala -274.06, a prognoza ruszyla sie o 0.00
   (wpis 274.06 w kategorii Energia Elektryczna)
E  AssertionError: karta zapowiedziala -374.06, a prognoza ruszyla sie o -44.06
   (wpis 374.06 w kategorii Energia Elektryczna)
```

Przypadek `[274.06-Zakupy]` **przeszedł na zielono i to jest poprawne**, nie luka: kategoria bez
pozycji planu obciąża oś całą kwotą, więc obie liczby są tam równe. Gdyby czerwieniło się
wszystkie pięć, znaczyłoby to, że strażnik reaguje na sam fakt zmiany, a nie na kłamstwo.

### M-D62-3 — dokładnie ta pułapka, przed którą ostrzegało zlecenie

Wpis 274,06 zł z pozycji planu 330,00 zł **nie przesuwa całej pozycji** — D-61 mówi „konsumuje aż
do zera", więc 55,94 zł zostaje na 20 X i użytkownik ten wypływ na Płynności zobaczy. Zdanie
mówiące „pozycja schodzi z osi w całości" byłoby fałszem widocznym na sąsiednim ekranie:

```
E  - ziernika; zostaje z niej 55,94 zł na 20 października
E  + ziernika; pozycja schodzi z osi w całości
```

### Czego ten przebieg NIE objął

- **Nie mutowano `_wejscia_planu`** — funkcji wydzielonej w tym zadaniu z `zbuduj`. Wydzielenie jest
  neutralne (suita przed i po: 880 passed), ale **żaden test nie pilnuje, że oba wołania dostają tę
  samą listę**; gdyby ktoś rozdzielił je z powrotem, nic by się nie zaczerwieniło. Etykieta jawna:
  **niepotwierdzone**. Próg: przy pierwszej zmianie reguły dnia płatności (`dzien_pozycji`).
- **Nie ma strażnika na zdanie w przeglądarce.** Testy czytają odpowiedź trasy, nie wyrenderowany
  ekran. Że wiersz z `po: null` rysuje się jako etykieta + wyjaśnienie, wiadomo z Z1 — nie
  z pomiaru wykonanego dziś.

---

## Przebieg 2026-08-29 — Z7c domknięcie: piąty wiersz karty widziany w przeglądarce (D-62)

**Co potwierdzano.** Max wdrożył D-62 po stronie silnika (SHA `db2b60a`), a jego testy czytają
**odpowiedź trasy**, nie wyrenderowany ekran. Różnica nie jest formalnością: ta noc wyprodukowała
sześć strażników-atrap i dwa narzędzia drukujące odwrotność prawdy. Potwierdzenie poszło więc
**wzrokiem w przeglądarce** plus pomiarem prostokątów, nie odczytem JSON-a.

**Zmierzone (Playwright, 1440×900, dzień 2026-10-06, baza `scratchpad/z7c.db`):** piąty wiersz stoi
na ekranie we **wszystkich pięciu** stanach brzmienia, mieści się w kolumnie karty
(`pozaKolumne: 0 px`, `naklada: false`, `scrollWidth` dokumentu 1440 = szerokość okna),
etykieta 63 px + wyjaśnienie 427 px w kolumnie 500 px.

**Kontrola liczności, która wyłapała własny błąd sondy.** Pierwszy przebieg mierzył wyjście poza
kolumnę względem elementu wybranego przez `querySelector('[class*="__kolumna"]')` — trafił
w `kolumnaKwoty` formularza (260 px) i zameldował „wiersz wychodzi poza kolumnę o 240 px"
dla **wszystkich pięciu wierszy, także tych sprzed D-62**. Sonda w złej warstwie melduje
awarię tak samo pewnie, jak sonda w dobrej melduje sukces. Poprawny pomiar bierze
`wiersz.closest('[class*="__kolumna"]')`.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-Z7c-7** | ramka `Ksiegowanie.dc.html` dostaje **piąty** wiersz siatki karty (symulacja przerysowania przez Milę) | `liczba wierszy karty w ramce zgadza się z wzorcem` | **czerwony** (1 failed / 38) |
| **M-Z7c-8** | wzorzec zliczający wiersze przestaje cokolwiek trafiać (`display: grid;` → `display:grid;`) | `liczba wierszy karty w ramce zgadza się z wzorcem` | **czerwony** (1 failed / 38) |

Kontrola po cofnięciu obu: **38 passed**. Mutacje wykonane w kopii poza repozytorium
(`scratchpad/mut-z7c`), na kopii ramek — **repozytorium `makiety/` nietknięte**.

M-Z7c-8 jest kontrolą dwustronną tego samego strażnika: pierwsza mutacja dowodzi, że test
czerwieni się na **zmianie ramki**, druga — że czerwieni się także wtedy, gdy **pomiar przestaje
cokolwiek widzieć**. Bez drugiej test przechodziłby po cichu w chwili, w której zmieni się
zapis stylu w ramce.

### Czego ten przebieg NIE objął — i to jest najważniejsza pozycja

**Bramka odwzorowania jest wobec piątego wiersza ŚLEPA.** `Ksiegowanie` daje **0,12% przed D-62
i 0,12% po D-62** — bo wzorcowy zestaw danych niesie kartę taką, jaką rysuje ramka, czyli
czterowierszową. To nie jest wada wzorca: wzorzec ma być rysunkiem. To jest **rozjazd ramki
z produktem**, który kosztuje (zmierzone w przeglądarce na żywym silniku) **+52 px** wysokości
strony w brzmieniach dwuwierszowych i **+70 px** w brzmieniu „w planie" — 1 024 i 1 042 px
wobec 972 px ramki. Różnica jest **układowa, nie tekstowa**: dochodzi cały wiersz.

Dług opisany przy `KSIEGOWANIE` w `interfejs/narzedzia/dane-wzorcowe.mjs`, z progiem:
**przy pierwszym przerysowaniu `Ksiegowanie.dc.html` wzorzec dostaje piąty wiersz**, a strażnik
M-Z7c-7 pilnuje, żeby ten moment nie przeszedł niezauważony.

---

## Przebieg 2026-08-29 — Z10, przegląd gałęzi (Leo)

Przebieg recenzenta, nie wykonawcy: mutacje pisane **przeciwko strażnikom, które
już stały**, żeby sprawdzić, czy strzegą tego, co deklarują. Wszystkie w kopii
drzewa poza repozytorium (`scratchpad/leo-mut`), kontrola bazowa `892 passed`.

| # | Co zmieniono | Który test padł | Wynik |
|---|---|---|---|
| M-L1 | `pieniadz.do_zlotych`: `ROUND_HALF_UP` → `ROUND_DOWN` | `test_stawki_jeden_nosnik.py::test_zaokraglenie_ma_JEDEN_nosnik_i_jest_nim_pieniadz` (+5) | **czerwony** |
| M-L3 | `podatki.zaplaty_podatkowe`: zdjęty filtr kategorii | `test_rezerwa.py::test_zaplata_liczy_sie_TYLKO_z_kategorii_podatkowej` (+5) | **czerwony** |
| M-L4 | `api/kwoty.kwota`: `str(x)` zamiast `str(pieniadz.do_groszy(x))` | `test_kontrakt_dwa_nosniki.py::test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ` | **czerwony** |
| M-L5 | `pieniadz.zabron_float`: zdjęta odmowa dla `float` | `test_kontrakt_dwa_nosniki.py::test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ`, `test_stawki_jeden_nosnik.py::test_zaokraglenie_ma_JEDEN_nosnik_i_jest_nim_pieniadz` | **czerwony** |
| M-L8 | `interfejs/lib/kontrakt.ts`: pole `saldoMinimalne` → `saldoMinimalneXX` | `test_kontrakt_dwa_nosniki.py::test_nazwy_pol_sie_ZGADZAJA[DanePlynnosci]` (+2) | **czerwony** |
| **M-L7** | `prognoza_plynnosci.py:409`: `stawki.do_groszy(...)` → `Decimal(f'{...:.2f}')` — drugi nośnik zaokrąglenia, inna reguła | **żaden** | **PRZEŻYŁA — `892 passed`** |

### M-L8 zamyka pozycję otwartą przez Z5

Ślad Z5 („Czego ten przebieg NIE objął") notował: *strona TypeScriptu nie była
mutowana, zgodność kontraktu wnioskowana z symetrii porównania*. **Zmierzone:**
mutacja po stronie `.ts` czerwieni trzy testy `test_kontrakt_dwa_nosniki.py`.
Pozycja schodzi z listy otwartych — porównanie działa w obie strony.

### M-L7 — strażnik, który pilnował jednego kształtu zapisu, nie reguły

`test_stawki_jeden_nosnik.py::test_kwota_nie_jest_liczona_wlasnym_quantize_poza_pieniadzem`
deklaruje, że kwot nie wolno zaokrąglać poza `silnik/pieniadz.py`. Szuka wyłącznie
`quantize(GROSZ | ZLOTY | Decimal("0.01") | Decimal("1"))`. Python zaokrągla też
opisem formatu — `f"{x:,.2f}"` — i tego wzorzec nie widzi. Podstawiony drugi
nośnik, działający **inną regułą** (`ROUND_HALF_EVEN` zamiast `ROUND_HALF_UP`),
w ścieżce kwoty prognozy płynności, przeszedł całą suitę.

To nie jest hipoteza. `silnik/rdzen/prezentacja.py:56` **już jest** takim drugim
nośnikiem — jedynym miejscem formatowania kwot w projekcie (`CLAUDE.md` §5).
Pomiar 2026-08-29:

```
 wartosc | silnik do_groszy | ekran prezentacja.zloty
   0.145 |             0.15 | 0,14 zł
   0.005 |             0.01 | 0,00 zł
  12.345 |            12.35 | 12,34 zł
   2.675 |             2.68 | 2,68 zł
```

Trzy z sześciu wartości dają **inny grosz**. Nagłówek `pieniadz.py` twierdzi
*„każde zaokrąglenie w tej aplikacji przechodzi przez ten plik"* — pomiar tego
nie potwierdza.

### Domknięcie — `testy/test_zaokraglenie_ekranu.py`

Dopisany strażnik zamyka klasę, nie jeden przypadek: skanuje `silnik/**` i `api/*`
za opisem formatu z dwoma miejscami po przecinku, z **jednym nazwanym wyjątkiem**
(`prezentacja.py`) i **jawnym progiem konsolidacji** — przy pierwszej zmianie
`prezentacja.liczba` formatowanie woła `pieniadz.do_groszy`, a wyjątek znika.

**Mutacja dowodząca (kontrola dwustronna):** ta sama M-L7, powtórzona po dopisaniu
strażnika, daje `1 failed, 894 passed` i czerwieni **dokładnie**
`test_zaokraglenie_ekranu.py::test_grosze_nie_sa_zaokraglane_OPISEM_FORMATU_poza_jednym_wyjatkiem`.
Kontrola po cofnięciu mutacji: `895 passed, 3 deselected`. Data: 2026-08-29.

### Czego ten przebieg NIE objął

1. **Odwzorowania ramek** — bramka pikselowa nie była uruchamiana ani mutowana
   w tym przeglądzie; stan przyjęty z raportów Z2b/Z7c.
2. **Ekranów w przeglądarce** — przegląd czytał kod i mierzył silnik, nie oglądał
   wyrenderowanych stron.
3. **`silnik/rdzen/narzedzia.py:238`** (`f"{...:.0f}"`) — zaokrąglenie **procentu**,
   nie kwoty; świadomie poza wzorcem nowego strażnika. Niepilnowane: że ten procent
   zaokrągla się tą samą regułą co reszta aplikacji.

---

## Przebieg 2026-08-29 — sprostowania po przeglądzie Z10 (Ethan)

Kopia drzewa poza repozytorium (`scratchpad/mut-z10`), `__pycache__` czyszczony przed **każdym**
przebiegiem. Kontrola bazowa kopii: **896 passed, 3 deselected**.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-L7** *(powtórzona za Leo, po mojej naprawie)* | drugi nośnik zaokrąglenia przez opis formatu w `prognoza_plynnosci.py:409` | `test_grosze_nie_sa_zaokraglane_OPISEM_FORMATU_poza_jednym_wyjatkiem` | **czerwony** |
| **M-L8** | zdjęte wołanie `pieniadz.do_groszy` z `prezentacja.liczba` — naprawa cofnięta | `test_ekran_i_silnik_zaokraglaja_TAK_SAMO` | **czerwony** |
| **M-L9** | `kod_pythona_bez_prozy` przestaje cokolwiek zdejmować | `test_regula_formatowania_kwoty_ma_JEDEN_nosnik_w_calym_projekcie` · `test_grosze_nie_sa_zaokraglane_OPISEM_FORMATU_poza_jednym_wyjatkiem` | **czerwony** |

Kontrola po cofnięciu wszystkich trzech: **896 passed, 3 deselected**.

### M-L7 — strażnik Leo nie stracił zębów po naprawie

To jest pytanie, które trzeba było zadać: naprawa mogła sprawić, że strażnik przechodzi
**„bo nie ma czego złapać"**. Nie przechodzi:

```
E  AssertionError: zaokraglanie kwot opisem formatu poza jedynym nosnikiem:
   ['prezentacja.py', 'prognoza_plynnosci.py']
```

Wyjątek `prezentacja.py` **został na liście** — i to jest właściwe zachowanie, bo `:,.2f` nadal
tam stoi, tylko **nie zaokrągla już niczego**: wartość dociera zaokrąglona. Drugi plik na liście
jest wadą i strażnik go widzi.

### M-L8 — kontrola odwrotna do zdjętego testu przypinającego

Leo przypiął **rozjazd**, żeby jego naprawa nie przeszła po cichu. Naprawa nastąpiła, więc test
przypinający zdjąłem — dokładnie tak, jak żądał jego własny docstring — i w jego miejsce postawiłem
kontrolę **zgodności**. M-L8 dowodzi, że nowa kontrola nie jest tautologią:

```
E  AssertionError: ekran i silnik znowu zaokraglaja inaczej: ['0.145', '0.005', '12.345']
```

Trzy te same wartości, które Leo zmierzył jako rozjeżdżone. Zamiana testu na „słabszy przy okazji
naprawy" byłaby tu najłatwiejszym błędem i tego właśnie ta mutacja pilnuje.

### M-L9 — nowy skaner robi robotę, a nie tylko ucisza

`kod_pythona_bez_prozy` powstał, bo mój nagłówek `pieniadz.py` **cytuje** zakazany kształt
`f"{x:,.2f}"`, żeby wyjaśnić, dlaczego jest zakazany — i zaczerwienił dwa strażniki naraz.
To trzecie trafienie tego wzorca w tym projekcie (M3 w Z1, M-Z7-1c w Z7).

Skaner mógłby uciszyć strażników przez oślepienie ich. **Nie oślepia** — dowód jest dwustronny:
M-L7 pokazuje, że prawdziwą wadę w kodzie nadal łapie; M-L9 pokazuje, że bez skanera guardy
czerwienią się na samej prozie. Granica: **proza wyjaśniająca regułę nie jest jej złamaniem;
napis, którego program używa, jest.**

### Czego ten przebieg NIE objął

- **Nie mutowano granicy typu** (`prezentacja` przyjmuje `float`). Naprawy nie było — to dług
  z progiem, opisany w nagłówku `silnik/pieniadz.py`.
- **Nie mutowano `podatki.zaplaty_podatkowe`.** Filtr okresu nie istnieje, więc nie ma czego
  mutować; dług z progiem, opisany w `silnik/pieniadz.py` i w `docs/PRD.md` §17 poz. 18.

---

## Przebieg 2026-08-29 — schemat 12: rejestr stawek w bazie + trzy kolumny z PRD §6.3 (Ethan)

**Co przybyło.** Tabela `rejestr_stawek` w bazie SQLite (napis SQL mieszka w `wiedza/rejestr.py`
jako `SCHEMAT_SQLITE`), zasilenie 19 pozycjami z `wiedza/stawki_poczatkowe.py` — **wszystkie
w statusie `proponowana`, żadna zatwierdzona** — oraz trzy kolumny z PRD §6.3:
`wpisy_budzetu.zrodlo`, `kategorie.niezbedna`, `przychody_jdg.data_obowiazku_vat`.
Nowi strażnicy: `testy/test_rejestr_sqlite.py` (13), `testy/test_trzy_kolumny.py` (10).

**Jak wykonywano.** Kopia drzewa poza repozytorium (`scratchpad/mut-ethan-0829`, kopia przez
`rsync` z wyłączeniem `node_modules`, `.venv`, `.next`), `__pycache__` czyszczony **przed każdym**
przebiegiem — także przed przebiegiem kontrolnym po cofnięciu. Kontrola bazowa kopii:
`919 passed, 3 deselected, 1 warning`. Baza roboczA nie brała udziału: każdy test stoi na własnym
pliku w katalogu tymczasowym.

| # | Co zmieniono w kodzie produkcyjnym | Który test padł | Wynik suity |
|---|---|---|---|
| M1b | `wiedza/rejestr.py`: kolumna `niezweryfikowane` zdjęta z `SCHEMAT` (dialekt PostgreSQL — napis **niewykonywany** w SQLite, więc mutacja nie psuje niczego poza regułą jednego nośnika) | `test_rejestr_sqlite.py::test_oba_dialekty_niosa_DOKLADNIE_kolumny_z_jednego_nosnika` | `1 failed, 917 passed` |
| M2 | `magazyn.zasiej_rejestr_stawek`: warunek idempotencji rozszerzony o `AND status = 'proponowana'` | `test_rejestr_sqlite.py::test_zasiew_NIE_WSKRZESZA_propozycji_po_zatwierdzeniu` | `1 failed, 917 passed` |
| M3 | `magazyn._DOPISYWANE_KOLUMNY`: usunięty wpis `("wpisy_budzetu", "zrodlo", …)` | `test_trzy_kolumny.py::test_stara_baza_DOSTAJE_kolumny_bez_utraty_wierszy` (+ 2 dalsze z tego pliku) | `3 failed, 915 passed` |
| M4 | `magazyn._SCHEMAT`: usunięta linia `niezbedna INTEGER,` | `test_trzy_kolumny.py::test_SAM_schemat_swiezej_bazy_NIESIE_trzy_kolumny` | `1 failed, 918 passed` |
| M5 | `magazyn._stawka_z_wiersza`: `Decimal(str(w[1]))` → `float(w[1])` | `test_rejestr_sqlite.py::test_wczytane_stawki_niosa_Decimal_a_nie_liczbe_zmiennoprzecinkowa` | `1 failed, 918 passed` |
| M6 | `silnik/rdzen/podatki.py`: dopisana funkcja wołająca `magazyn.wczytaj_stawki` (udawany konsument rejestru) | `test_rejestr_sqlite.py::test_rejestr_MA_dane_i_NIE_MA_konsumenta` | `1 failed, 918 passed` |
| M7 | `magazyn.polacz`: usunięte wywołanie `zasiej_rejestr_stawek(polaczenie)` | 7 testów `test_rejestr_sqlite.py`, m.in. `test_ponowne_otwarcie_NIE_DUBLUJE_rejestru` | `7 failed, 912 passed` |
| M8 | `magazyn._SCHEMAT`: `zrodlo … DEFAULT 'recznie'` → `DEFAULT 'historia-2025'` | `test_trzy_kolumny.py::test_zapis_wpisu_bez_podania_zrodla_daje_recznie` | `1 failed, 918 passed` |

**Kontrola po cofnięciu każdej mutacji: `919 passed, 3 deselected, 1 warning`.**

### M4 przeszła najpierw NA ZIELONO — i to jest najważniejsze znalezisko tego przebiegu

W pierwszym podejściu M4 (zdjęcie `niezbedna INTEGER,` z `magazyn._SCHEMAT`) dała
**`918 passed`, zero czerwonych**. Mutacja weszła — kontrola tekstowa po podmianie pokazała
`0` wystąpień wzorca w pliku. Strażnik `test_swieza_baza_MA_wszystkie_trzy_kolumny` jej nie
zobaczył.

**Przyczyna.** Kolumna ma **dwie drogi** do bazy: `_SCHEMAT` (baza świeża) i `_DOPISYWANE_KOLUMNY`
(baza istniejąca), a `polacz()` wykonuje **obie**. Test pytający „czy kolumna jest **po otwarciu
bazy**" nie odróżnia, którą drogą przyszła — zdjęcie jednej z nich było dla niego niewidoczne.
Mutacja **M4b**, zdejmująca kolumnę z **obu** nośników, czerwieniła trzy testy — czyli strażnik
nie był całkiem ślepy, ale pilnował słabszej własności, niż deklarował.

**Naprawa.** Dołożony `test_SAM_schemat_swiezej_bazy_NIESIE_trzy_kolumny`: wykonuje sam
`magazyn._SCHEMAT` na połączeniu w pamięci, **bez `polacz()`**, i pyta o trzy kolumny. Po naprawie
M4 czerwieni dokładnie ten jeden test (wiersz w tabeli wyżej). To ta sama klasa awarii, którą
konstytucja firmy opisuje jako „strażnik-atrapa": mechanizm dawał sygnał „w porządku", nie
sprawdzając tego, co miał sprawdzać.

### Ile rzeczy każdy strażnik widział — bo pusta baza jest dla strażników groźna

Test, który nic nie znalazł, bo nic nie ma, przechodzi tak samo jak test, który sprawdził
i potwierdził. Przy każdym strażniku zawartości stoi kontrola liczności:

| Strażnik | Ile rzeczy widział | Skąd wiadomo |
|---|---|---|
| `test_oba_dialekty_niosa_DOKLADNIE_kolumny_z_jednego_nosnika` | 14 kolumn po stronie PostgreSQL, 14 po stronie SQLite | `assert len(pg) >= 10` i `assert len(lite) >= 10` — parser, który zwrócił pustkę, porównałby pustkę z pustką |
| `test_rejestr_dostaje_WSZYSTKIE_pozycje_zasilenia` | 19 wierszy | `assert ile_w_module > 0` przed porównaniem liczności |
| `test_ZADNA_stawka_nie_jest_zatwierdzona` | 19 wierszy | `assert sum(stany.values()) > 0` |
| `test_jawna_watpliwosc_przezywa_droge_do_bazy` | 2 pozycje z wątpliwością | `assert ile_w_module > 0` |
| `test_rejestr_MA_dane_i_NIE_MA_konsumenta` | 31 plików `.py` w `silnik/` i `api/` | `assert len(pliki) >= 20` — wyszukiwanie, do którego nie dotarł żaden plik, zameldowałoby „zero konsumentów" przy skasowanym katalogu |
| `test_niezbedna_startuje_jako_NIE_WIEM_a_nie_jako_nie` | 24 kategorie | `assert len(wiersze) > 0` |
| `test_SAM_schemat_swiezej_bazy_NIESIE_trzy_kolumny` | 3 pary tabela–kolumna | `assert sprawdzone == 3` plus `assert istniejace` per tabela |

### Czego ten przebieg NIE objął

- **Nie mutowano wiezu `zatwierdzona_ma_podpis`** przez zdjęcie go ze `SCHEMAT_SQLITE` — taka
  mutacja psuje tworzenie tabeli i rozlewa czerwień po całej suicie, więc nie wskazuje strażnika.
  Zamiast niej stoi **kontrola dwustronna**: `test_baza_ODRZUCA_zatwierdzona_bez_podpisu`
  (odrzuca brak podpisu) i `test_baza_PRZYJMUJE_zatwierdzona_z_podpisem` (nie odrzuca wszystkiego).
- **Nie mutowano `data_obowiazku_vat` po stronie rachunku VAT** — konsumenta tej kolumny **nie ma**;
  silnik nadal sumuje VAT ze wszystkich faktur bez względu na okres. Dług z progiem,
  `docs/PRD.md` §6.3 p.3 i rozdz. 13.
- **Nie mutowano ścieżki podpięcia silnika pod rejestr** — nie istnieje. To jest dokładnie to,
  czego pilnuje strażnik progu M6.

---

## Przebieg 2026-08-29 (W1) — `testy/test_schemat_dwa_dialekty.py`

**Co pilnuje strażnik.** Dwa nośniki schematu bazy: dialekt SQLite
(`magazyn._SCHEMAT` + `rejestr.SCHEMAT_SQLITE`, nośnik żywy — z niego stoi baza)
i dialekt PostgreSQL (`silnik.baza.schemat_postgresql()` = `silnik/baza/schemat.sql`
+ `rejestr.SCHEMAT`, cel migracji). Do 2026-08-29 nic ich nie porównywało; pomiar
przyrządem `testy/porownanie_schematu.py` na commicie `0b282cc` dał **24 miejsca rozjazdu**
(plan sesji mówił o dziewięciu). Po W1 zostaje ich **9**, wszystkie w rejestrach
`WIEZY_TYLKO_POSTGRESQL` i `INDEKSY_TYLKO_POSTGRESQL` plus świadomy rozdział `rejestr_stawek`.

**Ile porównuje — liczby stoją w asercjach, nie w nazwach testów:**

| Wymiar | Ile |
|---|---|
| tabel po każdej stronie | 14 (asercja `== ILE_TABEL`, plus niezależne policzenie poleceń `CREATE TABLE`) |
| kolumn wspólnych | 95, każda w czterech wymiarach: typ, obowiązkowość, wartość domyślna, dziedzina |
| kolumn kwotowych z `_KWOTOWE` | 16 (asercja `== ILE_KOLUMN_KWOTOWYCH`) |
| więzów jednoznaczności | 4 (asercja `== ILE_WIEZOW_JEDNOZNACZNOSCI`) |
| dziedzin wyliczeniowych | 5 (`wpisy_budzetu.zrodlo`, `forma`, `kategorie.typ`, `status` i `jednostka` stawki) |
| więzów/indeksów tylko po stronie PostgreSQL | 5 + 3, wpisane imiennie do rejestru |

**Jak wykonywano.** Kopia drzewa poza repozytorium (`scratchpad/mut2`, `rsync` bez `.git`
i `.venv`), `PYTHONDONTWRITEBYTECODE=1` przy każdym przebiegu — dwie mutacje tej samej
długości w tej samej sekundzie potrafią uruchomić stary skompilowany kod i zameldować
cudzy wynik. Po każdej mutacji plik przywracany z kopii sprzed mutacji.

Kontrola przed mutacjami: **17 passed** (plik strażnika).

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M1** | `schemat.sql`: `zysk_netto NUMERIC(14,2) NOT NULL` → `NUMERIC(14,2)` | `test_OBOWIAZKOWOSC_kolumn_jest_ta_sama` | **czerwony** (1 failed, 16 passed) |
| **M2** | `schemat.sql`: `zaplacony_zus` → `zaplacony_zus_x` | `test_oba_dialekty_MAJA_te_same_kolumny` · `test_KAZDA_kolumna_kwotowa_jest_NUMERYCZNA_po_stronie_PostgreSQL` | **czerwony** (2 failed, 15 passed) |
| **M3** | `schemat.sql`: `forma IN ('SKALA','RYCZALT')` → `('SKALA','LINIOWY','RYCZALT')` | `test_DZIEDZINY_WARTOSCI_sa_te_same` · `test_dziedzina_formy_ZGADZA_SIE_z_FORMY_ZAPISYWALNE` | **czerwony** (2 failed, 15 passed) |
| **M4** | `schemat.sql`: `wpisy_budzetu.kwota NUMERIC(14,2)` → `DOUBLE PRECISION` (§3.1) | `test_TYPY_kolumn_odpowiadaja_sobie_rodzina_po_rodzinie` · `test_KAZDA_kolumna_kwotowa_jest_NUMERYCZNA_po_stronie_PostgreSQL` · `test_ZADNA_kolumna_nie_uzywa_typu_zmiennoprzecinkowego` | **czerwony** (3 failed, 14 passed) |
| **M5** | `porownanie_schematu._ciala_tabel` zwraca pusty słownik — przyrząd ślepnie | `test_parser_WIDZI_oba_napisy_a_nie_porownuje_pustki` + 12 dalszych | **czerwony** (13 failed, 4 passed) |
| **M6** | `magazyn._SCHEMAT`: zdjęty `CONSTRAINT forma_znana` z żywego nośnika SQLite | `test_DZIEDZINY_WARTOSCI_sa_te_same` · `test_dziedzina_formy_ZGADZA_SIE_z_FORMY_ZAPISYWALNE` · `test_wiezy_TYLKO_PostgreSQL_sa_te_z_rejestru` · `test_swieza_baza_ODRZUCA_forme_spoza_dwojki` | **czerwony** (4 failed, 27 passed) |
| **M7** | `schemat.sql`: powrót `DEFAULT ''` do `godziny.pkwiu` | `test_WARTOSCI_DOMYSLNE_sa_te_same` | **czerwony** (1 failed, 16 passed) |
| **M8** | `porownanie_schematu._ciala_tabel` gubi **jedną** tabelę po cichu (`wynik.pop("godziny")`) | `test_parser_WIDZI_oba_napisy_a_nie_porownuje_pustki` + 7 dalszych | **czerwony** (8 failed, 9 passed) |
| **M9** | `magazyn._SCHEMAT`: zdjęty `CONSTRAINT typ_znany` | `test_DZIEDZINY_WARTOSCI_sa_te_same` · `test_wiezy_TYLKO_PostgreSQL_sa_te_z_rejestru` | **czerwony** (2 failed, 15 passed) |

Kontrola po cofnięciu wszystkich dziewięciu mutacji (`diff -q` wobec kopii sprzed mutacji:
trzy pliki zgodne z oryginałem): **936 passed, 3 deselected, 0 skipped**.

### Co pokazały M5 i M8 — najważniejsze pozycje tej tabeli

**M5:** gdy przyrząd pomiarowy przestaje cokolwiek widzieć, **cztery testy z siedemnastu
nadal są zielone**. Jeden z nich, `test_oba_dialekty_MAJA_te_same_tabele`, jest zielony
**dlatego, że porównuje pustkę z pustką** — dokładnie ta klasa strażnika-atrapy, która przy
zielonej suicie nie strzeże niczego. Łapie ją wyłącznie kontrola liczności, która żąda
**dokładnie 14 tabel** po każdej stronie.

**M8:** cichej utraty **jednej** tabeli kontrola „czy zbiór niepusty" **by nie złapała** —
13 tabel to nadal niepusty zbiór. Łapie ją dopiero **niezależne policzenie poleceń
`CREATE TABLE`** (`ile_polecen_create_table`), dołożone w przeglądzie samokrytycznym.
Parser sprawdzający sam siebie nie sprawdza niczego.

### Czego ten przebieg NIE objął

- **Nie mutowano treści więzu `CHECK` innego niż `IN (...)`.** Parser porównuje takie więzy
  **po nazwie**, nie po treści: zmiana `CHECK (kwota >= 0)` na `CHECK (kwota >= -1)` przy tej
  samej nazwie **nie zaczerwieni niczego**. Luka nazwana, nie zamknięta.
- **Nie mutowano kolumn ani warunku `WHERE` indeksu częściowego** — parser widzi wyłącznie
  nazwę indeksu. Ta sama klasa luki.
- **Nie mutowano zachowania PostgreSQL na żywej bazie.** Baza w Neonie jest pusta do W4, więc
  cały ten strażnik porównuje **napisy DDL**, nie dwie działające bazy. Błąd składni w
  `schemat.sql` przeszedłby przez wszystkie siedemnaście testów. Jedyne testy pytające żywą
  bazę to `test_swieza_baza_ODRZUCA_forme_spoza_dwojki` i
  `test_swieza_baza_PRZYJMUJE_kazdy_typ_z_budzet_TYPY` — obydwa na SQLite.
- **Nie mutowano `_KWOTOWE`** jako nośnika listy kolumn pieniężnych. Nie jest listą pełną:
  `forma_opodatkowania.stawka_ryczaltu` i `zobowiazania.oprocentowanie` idą przez `Decimal`
  ręcznie, poza `_wczytaj`. Domyka je od drugiej strony
  `test_ZADNA_kolumna_nie_uzywa_typu_zmiennoprzecinkowego`.

---

## Przebieg 2026-08-29 — rozdział „otwórz" od „zmigruj" (W2)

**Co pilnują strażnicy.** `magazyn.polacz()` do tego dnia stawiało cały schemat przy każdym
wywołaniu, a połączenie jest zależnością **na żądanie HTTP** (`api/wspolne.polaczenie`). Pomiar
sondą `sqlite3.set_trace_callback` na świeżej bazie, commit `65baac3`:

```
LACZNIE polecen: 98
wg pierwszego slowa: {'PRAGMA': 12, 'SELECT': 21, 'CREATE': 15, 'BEGIN': 3, 'INSERT': 44, 'COMMIT': 3}
PISZACYCH/DDL: 59
```

Po rozdzieleniu `polacz()` wykonuje **jedno** polecenie — `PRAGMA user_version`, odczyt.
Plan sesji mówił o „dwunastu rzeczach"; pomiar mówi o 98 poleceniach, z czego 59 piszących.

**Dlaczego strażnik nie jest `grep`-em.** DDL wchodziło do `polacz()` **przez wywołania w środku**
(`_dopisz_kolumny`, `zasiej_kategorie`, `_przebuduj_plan_budzetu`), więc funkcja mogła nie zawierać
ani jednego słowa `CREATE` i nadal stawiać czternaście tabel. Strażnik mierzy to, co **dotarło do
sterownika**. Mutacja M3 poniżej odtwarza dokładnie ten kształt wady.

**Jak wykonywano.** Kopia drzewa poza repozytorium (`scratchpad/mutW2`, `rsync` bez `.git`,
`.venv`, `node_modules`), `PYTHONDONTWRITEBYTECODE=1` przy każdym przebiegu, jedna mutacja naraz,
plik przywracany z kopii sprzed mutacji. Kontrola przed mutacjami: **953 passed, 3 deselected**.

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M1** | `zmigruj()`: usunięty `polaczenie.executescript(_SCHEMAT)` — migracja przestaje stawiać tabele | `test_zmigruj_STAWIA_pelny_schemat_i_zasiewa` · `test_start_aplikacji_MIGRUJE_baze` · `test_polacz_PRZYJMUJE_baze_zmigrowana` + 50 dalszych | **czerwony** (53 failed, 616 passed, 284 errors) |
| **M2** | `api/index.cykl_zycia`: usunięte `magazyn.zmigruj()` — uchwyt startowy przestaje migrować | `test_start_aplikacji_MIGRUJE_baze` | **czerwony** (1 failed, **952 passed**) |
| **M3** | `polacz()`: DDL wraca **wywołaniem w środku** (`zmigruj(sciezka)` przed otwarciem) — bez słowa `CREATE` w funkcji | `test_polacz_NIE_WYKONUJE_ani_jednego_polecenia_piszacego` · `test_polacz_ODMAWIA_otwarcia_bazy_niezmigrowanej` · `test_bez_startu_zadanie_ODMAWIA_zamiast_pokazac_zera` · `test_zdejmowanie_kolumn_NIE_BIEGNIE_przy_otwarciu` | **czerwony** (4 failed, 949 passed) |
| **M4** | `_wymagaj_zmigrowanej`: warunek `wersja == WERSJA_SCHEMATU` → `True` — bramka przestaje odmawiać | `test_polacz_ODMAWIA_otwarcia_bazy_niezmigrowanej` · `test_bez_startu_zadanie_ODMAWIA_zamiast_pokazac_zera` | **czerwony** (2 failed, 951 passed) |
| **M5** | `_wymagaj_niesprzecznych_kolumn`: `sprzeczne = []` — strażnik nieodwracalnego `DROP COLUMN` milknie | `test_kolumna_naraz_dopisywana_i_zdejmowana_JEST_ODMOWA` | **czerwony** (1 failed, 952 passed) |
| **M6** | `ustaw_aktywnosc_kategorii`: zdjęty `polaczenie.rollback()` przed `raise` | `test_ZADNA_funkcja_nie_zglasza_bledu_po_zapisie_bez_rollback` · `test_odmowa_dezaktywacji_NIE_ZOSTAWIA_otwartej_transakcji` | **czerwony** (2 failed, 951 passed) |
| **M7** | `_podsluchaj` w strażniku zwraca pustą listę — **przyrząd pomiarowy ślepnie** | `test_polacz_NIE_WYKONUJE_ani_jednego_polecenia_piszacego` · `test_zmigruj_STAWIA_pelny_schemat_i_zasiewa` | **czerwony** (2 failed, 8 passed w pliku strażnika) |
| **M8** | `zmigruj()`: `stawek = zasiej_rejestr_stawek(...)` → `stawek = 0` — zasiew rejestru znika | `test_zmigruj_STAWIA_pelny_schemat_i_zasiewa` · 7 testów `test_rejestr_sqlite.py` | **czerwony** (8 failed) |

Kontrola po cofnięciu wszystkich ośmiu mutacji (`diff -q` wobec repozytorium — cztery pliki
zgodne): **953 passed, 3 deselected, 0 skipped**.

### Co pokazała M2 — najważniejsza pozycja tej tabeli

**Migracja przy starcie aplikacji ma w całej suicie DOKŁADNIE JEDNEGO strażnika.** Po usunięciu
`magazyn.zmigruj()` z uchwytu cyklu życia **952 testy z 953 pozostały zielone** — łącznie ze
wszystkimi testami HTTP, bo budują one `TestClient(aplikacja)` **bez** `with`, więc uchwytu
w ogóle nie uruchamiają, a bazę migrują sobie same w fiksturze.

To jest dokładnie ten kształt awarii, przed którym ostrzegała bramka zadania: *rozdzielić tak, że
migracja przestaje działać w produkcji, a suita jest zielona, bo fikstura stawia schemat inaczej*.
Jedynym testem, który przechodzi przez uchwyt startowy, jest
`test_start_aplikacji_MIGRUJE_baze` — i to on jako jedyny się zaczerwienił.

**Wniosek do W4:** przy podmianie sterownika ten test zostaje jedynym pomiarem drogi produkcyjnej.
Jeśli miałby zostać wyłączony albo przepisany, wyłączenie jest decyzją do zgłoszenia, nie
porządkiem.

### Co pokazała M3

Mutacja przywraca DDL do `polacz()` **przez wywołanie w środku**, nie przez wpisanie polecenia SQL.
Funkcja po mutacji nie zawiera ani jednego słowa `CREATE`, `ALTER` ani `INSERT` — `grep` na jej
ciele daje zero trafień, a baza dostaje 101 poleceń przy każdym otwarciu. Łapie to wyłącznie pomiar
na sterowniku.

### Czego ten przebieg NIE objął

- **Nie mutowano czterech z sześciu miejsc uzupełnionych o `rollback()`** (`zapisz_plan`,
  `ustaw_ustawienie`, `zapisz_forme`, `zapisz_stan_konta`). Ich gałąź `except sqlite3.Error` jest
  osiągalna tylko przez awarię sterownika. Pilnuje ich **strażnik źródłowy**
  (`test_ZADNA_funkcja_nie_zglasza_bledu_po_zapisie_bez_rollback`), zaczerwieniony mutacją M6 na
  piątym miejscu tej samej klasy — nie ich własną mutacją behawioralną. Luka nazwana.
- **Nie mutowano zachowania na PostgreSQL.** Cały ten przebieg stoi na SQLite; baza w Neonie jest
  pusta do W4. Zdanie „w PostgreSQL zachowanie będzie inne" pozostaje **niezweryfikowane
  pomiarem** — jest przesłanką planu, nie ustaleniem tego przebiegu.
- **Nie mutowano atomowości `zapisz_koszt` i `oznacz_fakture_zaplacona`** — świadomie odłożone do
  W4, ze strażnikami opisującymi stan dzisiejszy i jawnym progiem
  (`testy/test_transakcje_przed_postgresql.py`, nagłówek).

---

## Przebieg 2026-08-29 (W3) — strażnicy **przed** migracją na PostgreSQL

**Co pilnują.** Trzy wady, które po podmianie sterownika SQLite → psycopg **nie dałyby żadnego
sygnału**, bo dzisiejsze asercje mierzą coś, co po migracji przestaje o nich mówić. Strażnicy
powstali, **póki jeszcze widać stan poprawny**:

| Plik | Wada | Ile obejmuje |
|---|---|---|
| `testy/test_kwoty_pozostaja_dziesietne.py` | kwota wraca jako `float64` zamiast `Decimal` | **16 kolumn w 9 tabelach** (asercja `== ILE_KOLUMN_KWOTOWYCH`, stała wołana z `test_schemat_dwa_dialekty.py` — jeden nośnik) |
| `testy/test_komunikat_duplikatu_faktury.py` | zdanie „Faktura o tym numerze już jest" wisi na treści komunikatu sterownika | 2 gałęzie tłumaczenia + **10 klauzul `except sqlite3.…`** i **1 dopasowanie po treści** (pomiar) + 34 pliki `.py` przeszukane |
| `testy/test_null_nie_udaje_liczby.py` | `NULL` → `NaN`, prawdziwy w warunku `if` | **3 składy kolumny** × 3 wiersze + **9 kształtów wejścia sterownika** (4 braki, 5 liczb) |

**Pomiar, na którym stoi cały przebieg** (pandas 3.0.5, 2026-08-29). `pandas.read_sql` ma
`coerce_float=True` w **wartości domyślnej**. Sterownik oddający `Decimal` — czyli dokładnie to,
co poda psycopg na kolumnie `NUMERIC`:

```
surowy kursor: [('Decimal', Decimal('7034.72')), ('Decimal', Decimal('1234567890123456.8'))]
read_sql domyslnie -> dtypes: {'kwota': dtype('float64')}
coerce_float=False -> dtypes: {'kwota': dtype('O')}
```

Ten sam eksperyment stoi w suicie jako `test_sterownik_oddajacy_Decimal_ZAPALA_straznika` —
nie jako cytat z raportu, tylko jako wykonywalny przypadek.

**Jak wykonywano.** Kopia drzewa poza repozytorium (`scratchpad/mutW3`, `rsync` bez `.git`
i `.venv`), `PYTHONDONTWRITEBYTECODE=1` i czyszczenie `__pycache__` przed każdym przebiegiem.
Po każdej mutacji plik przywracany z kopii `scratchpad/mutW3-oryginal`.
Kontrola przed mutacjami: **28 passed** (trzy nowe pliki), **981 passed, 3 deselected** (cała suita).

| # | Mutacja (`silnik/rdzen/magazyn.py`) | Który test padł | Wynik |
|---|---|---|---|
| **M1** | `_wczytaj` przestaje zamieniać kolumny kwotowe na `Decimal` (zdjęta cała pętla po `_KWOTOWE`) | `test_KAZDA_z_szesnastu_kolumn_kwotowych_wraca_jako_Decimal` | **czerwony** (1 failed, 5 passed) |
| **M2** | `_wczytaj` mapuje `float(x)` zamiast `Decimal(str(x))` | `test_KAZDA_z_szesnastu_kolumn_kwotowych_wraca_jako_Decimal` | **czerwony** (1 failed, 5 passed) |
| **M3** | `_KWOTOWE` gubi po cichu jedną kolumnę (`koszty_jdg.kwota_vat`, 16 → 15) | `test_KAZDA_z_szesnastu_kolumn_kwotowych_wraca_jako_Decimal` | **czerwony** (1 failed, 5 passed) |
| **M4** | `_SCHEMAT`: `wpisy_budzetu.kwota TEXT` → `REAL` — sterownik zaczyna oddawać liczbę | `test_SUROWY_odczyt_z_bazy_nie_oddaje_liczby_zmiennoprzecinkowej` | **czerwony** (1 failed, 5 passed; **na całej suicie 2 failed, 979 passed**) |
| **M5** | `if "numer_faktury" in str(e)` → `if "faktura_numer" in str(e)` | `test_duplikat_numeru_MOWI_o_numerze_a_nie_o_bazie` | **czerwony** (1 failed, 5 passed) |
| **M6** | `if "numer_faktury" in str(e)` → `if True` — gałąź łapie każde naruszenie więzu | `test_INNE_naruszenie_wiezu_daje_komunikat_OGOLNY` · `test_ILE_miejsc_rozstrzyga_po_TRESCI_komunikatu_sterownika` · `test_ZADEN_INNY_modul_nie_rozstrzyga_po_tresci_komunikatu` | **czerwony** (3 failed, 3 passed) |
| **M7** | `except sqlite3.IntegrityError` → `except Exception` | `test_tlumaczenie_wyjatkow_OBEJMUJE_WYLACZNIE_sterownik_sqlite3` · `test_ILE_miejsc_rozstrzyga_po_TRESCI_komunikatu_sterownika` | **czerwony** (2 failed, 4 passed) |
| **M8** | `wczytaj_zobowiazania`: normalizacja `NaN` → `None` wyłączona (`if False`) | `test_kontrakt_trzyma_sie_przy_KAZDYM_skladzie_kolumny[mieszany]` · `test_odczyt_z_kolumny_NUMERYCZNEJ_tez_nie_przepuszcza_NaN` | **czerwony** (2 failed, 14 passed; na całej suicie 4 failed, 977 passed) |
| **M9** | `oprocentowanie_z_wiersza` przestaje rozpoznawać `NaN` (zdjęty człon `isinstance(w, float) and w != w`) | `test_oprocentowanie_z_wiersza_ROZUMIE_kazdy_ksztalt[nan-None-pandas po coerce_float na NULL]` | **czerwony** (1 failed, 15 passed) |
| **M10** | `_wczytaj` omija `pd.read_sql` (`cursor.fetchall()` + `pd.DataFrame`) — kształt zapowiedziany w W4 | `test_SUROWY_odczyt_z_bazy_nie_oddaje_liczby_zmiennoprzecinkowej` · `test_odczyt_z_kolumny_NUMERYCZNEJ_tez_nie_przepuszcza_NaN` | **czerwony** (2 failed, 20 passed) |

Kontrola po cofnięciu wszystkich dziesięciu mutacji (`diff -r` wobec kopii sprzed mutacji: różni się
wyłącznie `.pytest_cache`): **981 passed, 3 deselected, 0 skipped**.

### Co pokazała M4 — najważniejsza pozycja tej tabeli

Mutacja zmienia typ **jednej kolumny kwotowej** z `TEXT` na `REAL`, czyli robi to, co migracja zrobi
z szesnastoma naraz: sterownik zaczyna oddawać liczbę zmiennoprzecinkową. **979 testów z 981
pozostaje zielonych.** Zielony pozostaje też `test_KAZDA_z_szesnastu_kolumn_kwotowych_wraca_jako_Decimal`
z tego samego pliku — bo `_wczytaj` opakowuje liczbę z powrotem w `Decimal` **po** odczycie i strata
staje się niewidoczna dla każdej asercji patrzącej na wynik.

Łapie to wyłącznie strażnik podglądający `pandas.read_sql` **w locie**, czyli patrzący na ramkę
**taką, jaka wyszła ze sterownika**. To jest odpowiedź na pytanie „czy ten test zaczerwieni się po
podmianie sterownika": zaczerwieni, i wiadomo to **z pomiaru na stanie wytworzonym dzisiaj**,
nie z przypuszczenia.

### Co pokazała M10

Obydwa przyrządy — szpieg nad `pd.read_sql` i podstawiona ramka po-migracyjna — **wykrywają własne
oślepienie**. Gdy `_wczytaj` przestaje wołać `pd.read_sql` (a tak właśnie zapowiada W4: pandas nie
wspiera surowych połączeń psycopg), strażnik nie melduje sukcesu przy pustym pomiarze, tylko pada
z komunikatem „szpieg nie zobaczył ani jednego odczytu". Kontrola liczności działa.

### Czego ten przebieg NIE objął

- **Nie mutowano zachowania na PostgreSQL** — baza w Neonie jest pusta do W4. Wszystkie stany
  po-migracyjne są **wytworzone**: raz sterownikiem SQLite z konwerterem oddającym `Decimal`
  (`test_sterownik_oddajacy_Decimal_ZAPALA_straznika`), raz podstawioną ramką `float64`
  (`test_odczyt_z_kolumny_NUMERYCZNEJ_tez_nie_przepuszcza_NaN`), raz zmianą typu kolumny w schemacie
  (M4). Mechanizm jest ten sam — `coerce_float` w pandas — ale **zdanie „psycopg zachowa się tak
  samo" pozostaje niezweryfikowane pomiarem na żywej bazie**.
- **Nie zamknięto wady 2, tylko ją opisano.** Naprawa (tłumaczenie wyjątków psycopg) należy do W4.
  Znalezisko na przyszłość: PostgreSQL nada więzowi `numer_faktury TEXT NOT NULL UNIQUE`
  (`schemat.sql:86`, więz **bez nazwy własnej**) nazwę automatyczną
  `przychody_jdg_numer_faktury_key`, więc napis `"numer_faktury"` **będzie w komunikacie nadal** —
  dopasowanie po treści może przeżyć **przypadkiem**, opierając się na nazwie, której nikt nie
  wybrał. Zawiedzie natomiast klauzula `except sqlite3.IntegrityError`, bo `psycopg.errors.
  UniqueViolation` nie dziedziczy z `sqlite3.Error` — i razem z nią **zapasowe** „Zapis odrzucony
  przez bazę". To pilnuje `test_tlumaczenie_wyjatkow_OBEJMUJE_WYLACZNIE_sterownik_sqlite3`,
  **tripwire**: po naprawie w W4 zaczerwieni się raz, świadomie.
- **Nie objęto kolumn pieniężnych spoza `_KWOTOWE`** — `forma_opodatkowania.stawka_ryczaltu`
  i `zobowiazania.oprocentowanie` idą przez `Decimal` ręcznie, poza `_wczytaj`. Pierwszej pilnuje
  `test_forma_opodatkowania.py`, drugiej `test_null_nie_udaje_liczby.py`; **żadna z nich nie wchodzi
  do liczby 16**.
- **Nie mutowano `_stawka_z_wiersza`** (13 pozycji indeksowanych liczbą, sparowanych z ręcznie
  wypisaną kolejnością w `SELECT`) — to nazwane ryzyko W4, bez strażnika po tej stronie.
- **Nie mutowano ścieżki HTTP.** Wszystkie trzy strażniki kończą się na granicy magazynu. Czy
  `Decimal` przeżywa drogę przez `api/` i z powrotem, mówią inne pliki — ten przebieg tego nie
  mierzył.

---

## Przebieg 2026-08-29 — W4: podmiana sterownika SQLite → PostgreSQL

**Kontrola przed mutacjami** (kopia drzewa poza repozytorium, `PYTHONDONTWRITEBYTECODE=1`,
`__pycache__` czyszczone przed każdym przebiegiem): **991 passed, 3 deselected** na PostgreSQL 16
w kontenerze `doradca-postgres` (port 5434, baza `doradca_test`, przestrzeń nazw na test).

**Pułapka przyrządu, zmierzona przy tym przebiegu.** Pierwsze pięć mutacji uruchomiono z jawnym
`-q` w komendzie. `pytest.ini` ma `-q` w `addopts`, więc powstało `-qq` — i **linia podsumowania
zniknęła**; raport pokazywał wyłącznie nazwy testów, bez liczb. Przebieg powtórzono bez dodatkowego
`-q`. Liczby poniżej pochodzą z powtórzenia.

| # | Mutacja | Który test padł | Wynik | Kontrola po cofnięciu |
|---|---|---|---|---|
| **M-W4-1** | `magazyn._ramka`: ramka rzutowana na `float64` po odczycie (odtworzenie tego, co robi `coerce_float`) | `test_SUROWY_odczyt_z_bazy_nie_oddaje_liczby_zmiennoprzecinkowej` | `1 failed, 5 passed` | `6 passed` |
| **M-W4-2** | `magazyn.WIEZ_NUMER_FAKTURY` → `"przychody_jdg_numer_faktury_key"` (nazwa **automatyczna**, czyli ta, której nikt nie wybrał) | `test_PRAWDZIWA_baza_podaje_te_sama_nazwe_wiezu` · `test_duplikat_numeru_MOWI_o_numerze_a_nie_o_bazie` · `test_nazwa_wiezu_z_KODU_zgadza_sie_z_nazwa_z_BAZY` · `test_rozpoznanie_NIE_TRAFIA_w_wiez_o_nazwie_AUTOMATYCZNEJ` · `test_wiez_numeru_faktury_MA_NAZWE_ktora_zna_kod` | `5 failed, 18 passed` | `23 passed` |
| **M-W4-3** | `silnik/baza/schemat.sql`: `NOT NULL` → `NOT NUL` (błąd składni) | 16 testów `test_schemat_wobec_bazy.py`, w tym `test_napis_DDL_DA_SIE_wykonac_a_nie_tylko_sparsowac` | `3 failed, 13 errors` | `16 passed` |
| **M-W4-4** | `magazyn._kopia_przed_migracja`: zawsze `return None` (kopia po cichu nie powstaje) | `test_migracja_ZOSTAWIA_kopie_w_wersji_sprzed` · `test_kopia_PRZENOSI_WSZYSTKIE_wiersze_a_nie_same_tabele` · `test_kopia_DA_SIE_odtworzyc` · `test_kopia_ISTNIEJACA_zatrzymuje_migracje_zanim_ruszy` · `test_nazwa_kopii_niesie_ZNACZNIK_CZASU_co_do_minuty` · `test_nazwa_kopii_niesie_nazwe_KOPIOWANEJ_przestrzeni` · `test_migracja_z_OSEMKI_doklada_tabele_i_ZOSTAWIA_kopie` | `7 failed, 14 passed` | `21 passed` |
| **M-W4-5** | `magazyn.odtworz_z_kopii`: pętla wgrywająca wiersze zamieniona na `pass` (kopia jest, odtworzyć się nie da) | `test_kopia_DA_SIE_odtworzyc` | `1 failed, 11 passed` | `12 passed` |
| **M-W4-6** | `magazyn.zapisz_koszt`: powrót do DWÓCH osobnych zapisów z zatwierdzeniem każdego | `test_zapisz_koszt_ZATWIERDZA_RAZ_a_nie_dwa_razy` · `test_zapisz_koszt_NIE_ZOSTAWIA_osieroconego_wpisu_gdy_drugi_zapis_padnie` · `test_lista_ATOMOWYCH_jest_KOMPLETNA` | `3 failed, 5 passed` | `8 passed` |
| **M-W4-7** | `magazyn._zapisz`: rozpoznanie duplikatu z powrotem po TREŚCI komunikatu (`if "numer_faktury" in str(e)`) | `test_rozpoznanie_NIE_ZALEZY_od_tresci_komunikatu` · `test_rozpoznanie_NIE_TRAFIA_w_wiez_o_nazwie_AUTOMATYCZNEJ` · `test_ILE_miejsc_rozstrzyga_po_TRESCI_komunikatu_sterownika` · `test_ZADEN_INNY_modul_nie_rozstrzyga_po_tresci_komunikatu` | `4 failed, 3 passed` | `7 passed` |
| **M-W4-8** | `magazyn.czy_lokalny`: zawsze `True` (każdy serwer uznany za maszynę lokalną) | `test_pod_pytestem_serwer_ZDALNY_jest_BLEDEM` · `test_opis_bazy_przy_serwerze_ZDALNYM_mowi_ze_produkcyjna` | `2 failed, 14 passed` | `16 passed` |
| **M-W4-9** | `magazyn.adres_bez_hasla`: zwraca adres SUROWY (z hasłem) | `test_ZADEN_opis_ani_komunikat_NIE_NIESIE_hasla` · `test_podpis_zrodla_NIGDY_nie_niesie_hasla` · `test_opis_bazy_mowi_ktora_baze_otwarto` | `3 failed, 50 passed` | `53 passed` |
| **M-W4-10** | `magazyn.zmigruj`: DDL znowu wykonywany w całości, PRZED dołożeniem brakujących kolumn | `test_stara_baza_DOSTAJE_kolumny_bez_utraty_wierszy` · `test_stara_baza_znaczy_wiersze_sprzed_migracji_jako_RECZNE` · `test_stara_baza_dostaje_kolumne_BEZ_wiezu_i_to_jest_nazwane` | `3 failed, 7 passed` | `10 passed` |
| **M-W4-11** | `magazyn._wczytaj`: bramka `_TABELE_ZNANE` wyłączona (`if False`) | `test_ODCZYT_idzie_wylacznie_do_tabel_ze_SCHEMATU` | `1 failed, 15 passed` | `16 passed` |
| **M-W4-12** | jeden literał SQL wraca do znacznika SQLite (`klucz = %s` → `klucz = ?`) | `test_ZADEN_literal_SQL_nie_niesie_placeholdera_SQLite` | `1 failed, 15 passed` | `16 passed` |

**Dwanaście mutacji, dwanaście czerwonych, zero strażników-atrap w tym zestawie.**

### Trzy progi, które zadziałały — i strażnicy, którzy zaczerwienili się CELOWO

Wszystkie trzy były wcześniej zapisane jako dług z jawnym progiem „przy W4":

1. **`test_transakcje_przed_postgresql.py`** („te dwa strażniki mają wtedy zaczerwienić się
   CELOWO") → plik przemianowany na `test_transakcje.py`, dwa strażniki **odwrócone**: pilnują
   teraz, że atomowość JEST, a nie że jej nie ma. Poprzednie brzmienie: `assert ile == 2` oraz
   `assert po == przed + 1` („osierocony wpis budżetu miał zostać").
2. **`test_komunikat_duplikatu_faktury.py`** (tripwire `1 / 10 / 1` → „mają zejść do zera") →
   liczby zeszły do `0 / 0 / 0`, dołożona czwarta: `ILE_KLAUZUL_EXCEPT_PSYCOPG = 17` jako kontrola
   liczności, żeby trzy zera nie były prawdziwe także dla modułu bez żadnego tłumaczenia błędów.
3. **`wiedza/rejestr.SCHEMAT_SQLITE`** i **`magazyn._SCHEMAT`** („napis znika w chwili przejścia
   bazy na PostgreSQL") → oba skasowane; `test_schemat_dwa_dialekty.py` zastąpiony przez
   `test_schemat_wobec_bazy.py`, który porównuje napis DDL z **bazą postawioną z tego napisu**.

### Czego ten przebieg NIE objął

- **Nie mutowano ścieżki HTTP po podmianie sterownika.** Że `Decimal` przeżywa drogę przez `api/`
  i z powrotem, mówi `test_trasy_dwa_ekrany.py::test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej`
  (zielony, z asercją na liczbę odwiedzonych liści) — ale **żadna mutacja W4 nie celowała w tę
  granicę**. Poprzedni przebieg mutował `kwota()` i pokazał, że pięć z sześciu ścieżek z `float`
  leży poniżej pierwszego poziomu; ten przebieg tego nie powtórzył.
- **Nie mutowano bazy produkcyjnej.** Schemat postawiony w Neonie (2026-08-29) jest zweryfikowany
  odczytem (15 tabel, 24 kategorie, 19 stawek, forma 2026 = `SKALA`), ale **nie mutacją** —
  mutowanie produkcji nie wchodzi w grę, a strażnicy biegną na bazie lokalnej.
- **Nie mutowano izolacji testów.** Że każdy test dostaje własną przestrzeń nazw, jest widoczne
  z zieleni całej suity, ale **nie ma strażnika, który by się zaczerwienił, gdyby izolacja
  zniknęła** — dwa testy dzielące tabele nie muszą zderzyć się od razu. To jest **nazwana luka
  dla W5**.
- **Nie zmierzono czasu zimnego startu** ani liczby jednoczesnych sesji przy prawdziwym ruchu.
  Suita otwiera połączenie na test; produkcja otwiera je na żądanie HTTP i limit sesji u dostawcy
  jest zasobem. To należy do W6.

---

## Przebieg W5 — testy migracji (Quinn, 2026-08-29)

Zadanie: audyt pokrycia utraconego przy podmianie sterownika (W4) + domknięcie dwóch luk,
które wykonawca W4 nazwał sam w sekcji „Czego ten przebieg NIE objął" wyżej.

### Skąd wzięte liczby audytu — pomiar, nie przepisanie z nośnika

Zbiory identyfikatorów testów zebrane `pytest --collect-only` na obu commitach, w kopiach drzewa
poza repozytorium (`git archive cdd94ed` i `git archive ded8b2a`), i porównane `comm`:

```
W3 (cdd94ed): 981/984 tests collected (3 deselected)
W4 (ded8b2a): 993 collected
zdjęte: 56 · dołożone: 68 · kontrola: 981 − 56 + 68 = 993
```

**Nośnik twierdzi co innego niż pomiar.** Opis commita `ded8b2a` mówi „zdjęto 64 testy, weszło 75";
pomiar po identyfikatorach daje **56 i 68**. Plan (`docs/plan-chmura-2026-08-29.md`, W5) mówi
o „~101 testach w 11 plikach" z „~40 bez odpowiednika 1:1"; pomiar pokazuje **56 zdjętych z 9
plików**, z czego bez odpowiednika o tej samej nazwie — **35**, a bez jakiegokolwiek następcy —
**jeden** (niżej). Różnica bierze się z jednostki liczenia: nośniki liczyły testy w plikach
ruszonych, pomiar liczy identyfikatory, które faktycznie zniknęły z zebrania.

### Znalezisko audytu: jedna reguła została bez strażnika

| | |
|---|---|
| **Zdjęty test** | `test_schemat_dwa_dialekty.py::test_WARTOSCI_DOMYSLNE_sa_te_same` |
| **Czego pilnował** | wartości domyślnych (`DEFAULT`) kolumna po kolumnie, z progiem „co najmniej 90 kolumn" |
| **Dlaczego przedmiot ISTNIEJE** | baza niesie 22 wartości domyślne, a **trzy kolumny nie mają jej świadomie** i powód stoi przy każdej w `schemat.sql` (`przychody_jdg.pkwiu`, `godziny.pkwiu`, `przebiegi_straznika.kiedy`) |
| **Dowód, że nie pilnuje nic** | `grep -rn porownaj_domyslna testy silnik api wiedza migracja` → **jedno trafienie, sama definicja**; zero wołających |
| **Następca** | `testy/test_wartosci_domyslne.py` (nowy, W5) |

### Mutacje W5

| # | Mutacja | Który strażnik padł | Wynik | Po cofnięciu |
|---|---|---|---|---|
| **M-A1** | `schemat.sql`: `pkwiu TEXT NOT NULL` → `... NOT NULL DEFAULT ''` (dokładnie ta dziura, dla której zbudowano zdjętego strażnika) | **przed W5: żaden** · po W5: `test_wartosci_domyslne.py::test_kolumna_bez_wartosci_domyslnej_NADAL_jej_nie_ma[przychody_jdg-pkwiu]` · `test_ZBIOR_kolumn_z_wartoscia_domyslna_jest_TEN_z_rejestru` | **przed W5: `993 passed` — zero czerwonych** · po W5: `2 failed, 1013 passed` | `1015 passed` |
| **M-B1a** | `conftest.py`: `test_{os.getpid()}_{n}` → `test_0_{n}` (numer procesu wypada z nazwy przestrzeni) | `test_izolacja_testow.py::test_przestrzen_NIESIE_numer_TEGO_procesu` (+ `test_przestrzen_POPRZEDNIEGO_testu_ZNIKNELA` i `test_CUDZE_przestrzenie_NIE_czerwienia_tego_pliku` — obie kontrole liczności rozpoznania) | `3 failed, 4 passed` | `7 passed` |
| **M-B1b** | `conftest.py`: `_LICZNIK["n"] += 1` → `+= 0` (dwa testy jednego procesu w tej samej przestrzeni) | `test_KAZDY_test_dostaje_INNA_przestrzen` (+ kontrola liczności `test_przestrzen_POPRZEDNIEGO_testu_ZNIKNELA`) | `2 failed, 5 passed` | `7 passed` |
| **M-B1c** | `conftest.py`: pętla `DROP SCHEMA` w sprzątaniu zamieniona na `pass` | `test_przestrzen_POPRZEDNIEGO_testu_ZNIKNELA` — **dokładnie jeden** | `1 failed, 6 passed` | `7 passed` |
| **M-B2-1** | `api/kwoty.py`: `kwota()` zwraca `float(...)` zamiast `str(...)` — **granica HTTP po podmianie sterownika, luka nazwana wyżej** | `test_trasy_dwa_ekrany.py::test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej` + 34 dalsze | `35 failed, 980 passed` | `1015 passed` |
| **M-B2-2** | `api/kwoty.py`: `kwota()` zwraca `str(float(...))` — **typ zostaje napisem, wartość gubi grosz, kod 200** | **przed W5: `test_kotwica_PRZYJMUJE_kwote_ujemna` — przypadkiem, jednym napisem wpisanym na sztywno** · po W5: `test_kwota_przez_granice.py::test_KAZDA_kwota_przechodzi_granice_z_DWOMA_miejscami_po_kropce` · `test_kwota_ZACHOWUJE_koncowe_zero_bo_to_ONO_znika` · `test_obchod_NAPRAWDE_lapie_kwote_bez_grosza` | **przed W5: `1 failed, 1007 passed`** · po W5: `4 failed, 1011 passed` | `1015 passed` |

Wszystkie mutacje zakładane w **kopii drzewa poza repozytorium**
(`git archive ded8b2a | tar -x` do katalogu roboczego sesji), z `PYTHONDONTWRITEBYTECODE=1`
i czyszczeniem `__pycache__` przed każdym przebiegiem. Po M-B1c przestrzenie pozostałe w bazie
testowej skasowane ręcznie (7 sztuk, wszystkie po martwych procesach — sprawdzone `os.kill(pid, 0)`).

### Drugie znalezisko: granica HTTP pilnowała TYPU, nie WARTOŚCI

M-B2-1 i M-B2-2 różnią się jedną funkcją zewnętrzną, a ich skutek jest zupełnie inny. Pierwsza
zmienia **typ** i pada na niej strażnik odpowiedzi (`OdpowiedzJSON.render`) z listą ścieżek.
Druga zostawia **napis**, więc odpowiedź wychodzi z kodem **200** i cicho złą liczbą — dokładnie
awaria opisana w nagłówku `api/kwoty.py` („`Decimal("8623.10")` → `8623.1`, końcowe zero znikło").
Przed W5 łapał ją **jeden test i przypadkiem**: `test_kotwica_PRZYJMUJE_kwote_ujemna` porównuje
`saldoPoDniu` z napisem `"-500.00"` wpisanym na sztywno. Strażnik jednostkowy
`test_kontrakt_dwa_nosniki.py::test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ` **przechodził**,
bo żaden z jego trzech przykładów nie ma **końcowego zera** — a to właśnie ono znika.

### Czego przebieg W5 NIE objął

- **Nie mutowano bazy produkcyjnej w Neonie** — jak w W4, i z tego samego powodu.
- **Nie sprawdzono zachowania przy DWÓCH równoległych przebiegach naraz.** Strażnik izolacji
  odróżnia własne przestrzenie od cudzych po numerze procesu i to jest zmierzone jednostkowo
  (M-B1a), ale **nie odpalono dwóch suit jednocześnie**, żeby zobaczyć to na żywo.
- **Nie zbadano wartości domyślnych kolumn dokładanych `ALTER TABLE`** na starej bazie poza
  `_DOPISYWANE_KOLUMNY`; nowy strażnik czyta bazę **po** migracji świeżej, nie po każdej ścieżce
  migracyjnej.
- **Nie sprawdzono treści więzów `CHECK` innych niż `IN (...)`** — ta luka była nazwana już
  w nagłówku `test_schemat_wobec_bazy.py` i W5 jej nie ruszało.

---

## W7 — pasek prowadzi tam, gdzie obiecuje (2026-08-29)

**Stan przed zmianą, zmierzony `curl` na zbudowanej aplikacji (nie odczytany z kodu):**
dziewięć z dziewięciu odsyłaczy paska = **HTTP 404**, w tym odsyłacz do ekranu Płynności, który
stał wtedy pod `/`. Cały widoczny tekst strony `/miesiac` brzmiał
`Doradca Finansowy 404: This page could not be found. 404 This page could not be found.` —
po angielsku, bez zdania o tym, co się stało i co z tym zrobić (łamie CLAUDE.md §3.7 i §4).

Nowi strażnicy: `testy/test_odsylacze_paska.py` (pięć testów, statyczne) oraz
`interfejs/narzedzia/straznik-odsylacze-paska.mjs` (przejście przeglądarką po całym nagłówku).

**Wszystkie mutacje wykonane na kopii drzewa poza repozytorium**
(`scratchpad/kopia-w7`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`), z kontrolą
przed i po. Kontrola startowa kopii: `5 passed in 0.20s`.

| # | Co zmieniono | Który strażnik padł (po nazwie) | Wynik |
|---|---|---|---|
| **M-W7-1** | skasowana trasa zastępcza `interfejs/app/[ekran]/page.tsx` | `test_kazdy_klucz_paska_MA_GDZIE_prowadzic` **oraz** `test_trasa_bez_ekranu_NIE_MA_wpisanej_listy_ekranow` (`2 failed, 3 passed`) | **czerwony** |
| **M-W7-2** | skasowany `interfejs/app/plynnosc/page.tsx` — ekran wraca pod `/` | `test_ekran_plynnosci_STOI_POD_swoim_kluczem` (`1 failed, 4 passed`) | **czerwony** |
| **M-W7-3** | do trasy zastępczej dopisana gałąź `ekran === "budzet" ? ZNANE[2] : undefined` — klucz ekranu wpisany w kodzie | `test_trasa_bez_ekranu_NIE_MA_wpisanej_listy_ekranow` (`1 failed, 4 passed`) | **czerwony** |
| **M-W7-4** | skasowany `interfejs/app/not-found.tsx` | `test_nieznany_adres_MOWI_PO_POLSKU_co_sie_stalo` (`1 failed, 4 passed`) | **czerwony** |
| **M-W7-5** | `powloka.tsx`: `href={\`/${e.klucz}\`}` → `href="/plynnosc"` | `test_zaden_odsylacz_naglowka_NIE_JEST_wpisany_recznie` (`1 failed, 4 passed`) | **czerwony** |
| **M-W7-6** | skasowana trasa zastępcza + przebudowa i przebieg po adresach | `straznik-odsylacze-paska.mjs`, **kod wyjścia 1**, osiem wierszy `NIE PROWADZI — kod 404` | **czerwony** |
| **M-W7-7** | `powloka.tsx`: `PASEK.map` → `PASEK.slice(0, 3).map` | `straznik-odsylacze-paska.mjs`, **kod wyjścia 2**: „pasek oddał 3 odsyłaczy, mapa ekranów ma 9" | **czerwony (błąd pomiaru)** |

**Kontrola po cofnięciu każdej mutacji:** `5 passed` (testy statyczne) i `kod wyjścia 0`,
`Sprawdzonych adresów: 11`, `WYNIK: każdy odsyłacz prowadzi` (przejście przeglądarką).
Pliki kopii porównane `diff` z repozytorium po cofnięciu — identyczne.

### Dlaczego M-W7-7 jest osobną mutacją, a nie odmianą M-W7-6

M-W7-6 sprawdza, że strażnik **znajduje zepsuty odsyłacz**. M-W7-7 sprawdza coś innego: że
strażnik **wie, ile rzeczy zobaczył**. Bez kontroli liczności pasek okrojony do trzech pozycji
przeszedłby jako „zero błędnych odsyłaczy" — sprawdzenie, do którego nic nie dociera, melduje
sukces. Dlatego niekompletny pasek kończy **kodem 2 (błąd pomiaru)**, nie kodem 0 i nie kodem 1.

### Znalezisko po drodze: pierwsze brzmienie mówiło nieprawdę na jednym z jedenastu adresów

Ekran zastępczy mówił początkowo `»X« stoi w pasku, bo ma odpowiadać na pytanie …`. Na
`/co-mnie-czeka` było to **fałszem**: „Co mnie czeka" jest rozwinięciem otwieranym przyciskiem
z ekranu Płynności, nie pozycją paska (`makiety/ekrany.py`, `ROZWINIECIA`). Wykryte **odczytem
wyrenderowanego ekranu**, nie czytaniem kodu i nie przez żaden test — zdanie było poprawne
składniowo i przechodziło wszystko. Brzmienie skrócone do `»X« ma odpowiadać na pytanie …`,
prawdziwego dla obu rodzajów pozycji.

### Sprostowanie nośnika przy okazji

`interfejs/lib/ekrany.ts` wskazywał strażnika mapy ekranów pod adresem `testy/test_mapa_ekranow.py`.
**Pomiar: `ls testy/test_mapa_ekranow.py` → `No such file or directory`.** Strażnik istnieje, ale
w `testy/test_nosniki.py` (linia 41). Poprawka jest w komentarzu, nie w kodzie — kodu nie trzeba
było dotykać.

### Czego przebieg W7 NIE objął

- **Nie mierzono na wdrożeniu w chmurze** — wszystkie liczby pochodzą z lokalnej budowy
  produkcyjnej (`npm run build` + `next start`). Wdrożenie prowadzi Eva.
- **Nie zbudowano żadnego z siedmiu brakujących ekranów** — to był jawny zakres zadania.
- **Nie sprawdzono zachowania odsyłaczy przy wyłączonym JavaScript** ani czytnikiem ekranu.
- **Zaobserwowana, niewyjaśniona chwiejność `not-found.tsx` w trybie deweloperskim
  (Turbopack, Next 16.3.3):** przy jednym zimnym starcie strona nieznanego adresu oddała pustą
  powłokę błędu zamiast ekranu, przy kolejnych — poprawny ekran. **Na budowie produkcyjnej
  nie powtórzyło się ani razu** (trzy niezależne przebiegi strażnika, `kod wyjścia 0`).
  Przyczyny nie ustalono; zapisane, bo dotyczy tylko trybu deweloperskiego.

---

## Przebieg 2026-08-29 — W8, kontrolka stanu konta

Kontrola przed mutacjami: **41 passed** (`testy/test_ekran_plynnosc.py` +
`testy/test_ekran_ksiegowanie.py`) · **47 passed** (`npx vitest run`) ·
**kod wyjścia 0** (`straznik-ekran-wobec-silnika.mjs` na czystej bazie).

Kopia drzewa poza repozytorium (`scratchpad/mutacje-w8`), `PYTHONDONTWRITEBYTECODE=1`.
Wyjątek nazwany: **M-W8-7 i M-W8-8 wykonano w drzewie roboczym**, bo wymagają zbudowanej
wersji produkcyjnej i uruchomionego silnika, których kopia nie ma. Oba pliki po cofnięciu
porównane `diff` z kopią sprzed mutacji — **identyczne bajt w bajt**.

### Mutacje treści

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-W8-1** | `kotwica.tsx`: zdjęty `autoFocus` z pola kwoty | `test_zapis_stanu_konta_KOSZTUJE_NAJWYZEJ_TRZY_DOTKNIECIA` | **czerwony** |
| **M-W8-2** | `kotwica.tsx`: znak gubiony przy składaniu kwoty (`` `-${odczyt.kwota}` `` → `odczyt.kwota`) — debet 1 240,50 zł zapisałby się jako majątek | `test_kwota_stanu_konta_WOLNO_miec_ujemna` | **czerwony** |
| **M-W8-3** | `kotwica.tsx`: data przestaje być wypełniona z góry (`useState(DANE.odczyt)` → `useState("")`) | `test_zapis_stanu_konta_KOSZTUJE_NAJWYZEJ_TRZY_DOTKNIECIA` | **czerwony** |
| **M-W8-7** | `lib/kwota.ts`: `odczytajKwote` zdejmuje minus i oddaje stan `ok` zamiast `ujemna` | `odczyt-kwoty.test.ts > kwota UJEMNA jest rozpoznana, a nie odrzucona — konto na debecie` | **czerwony** |

### Mutacje liczności — „ile rzeczy pomiar faktycznie widział"

| # | Mutacja | Który test padł | Wynik |
|---|---|---|---|
| **M-W8-4** | `kotwica.tsx`: jedno z jedenastu brzmień przestaje być pokazywane (`setBladKwoty(NAPISY_KOTWICY.kwotaPusta)` → `setBladKwoty(null)`) — pusty formularz milczy | `test_kontrolka_MA_KOMPLET_brzmien_i_zadnego_u_siebie` (`pokazywanych jest 10 z 11 brzmien`) | **czerwony** |
| **M-W8-5** | `kotwica.tsx`: własna kopia reguły kształtu kwoty zamiast wołania `lib/kwota.ts` — nośnik wołany z jednego miejsca zamiast dwóch | `test_ksztalt_kwoty_MA_JEDEN_nosnik` | **czerwony** |
| **M-W8-6** | `test_ekran_plynnosc.py`: lista ramek okrojona do zera (`glob("*.dc.html")` → `glob("ZadnaTakaRamka*.dc.html")`) | `test_ZADNA_ramka_NIE_RYSUJE_pola_wpisywania` (`pomiar objal tylko 0 ramek`) | **czerwony** |
| **M-W8-8** | `kotwica.tsx`: zapis dochodzi do bazy, ale ekran nie dostaje odświeżonych danych (`poZapisie(dane)` usunięte) | `straznik-ekran-wobec-silnika.mjs`, **kod wyjścia 2**: `porównano 1 liczb, próg to 3` | **czerwony (błąd pomiaru)** |

**Kontrola po cofnięciu każdej mutacji:** `41 passed`, `47 passed`, `kod wyjścia 0`
(`Porównanych liczb: 5`, `WYNIK: zgodne`). Pliki porównane `diff` — identyczne.

### Dlaczego M-W8-8 jest osobną mutacją, a nie odmianą M-W8-2

M-W8-2 sprawdza, że strażnik **widzi złą liczbę**. M-W8-8 sprawdza coś innego: że strażnik
**wie, ile liczb zobaczył**. Bez kontroli liczności ekran, który nie dostał odświeżonych danych,
pokazuje pustą księgę i „zero rozjazdów" — czyli sprawdzenie, do którego nic nie dociera,
melduje sukces. Dokładnie ten wzorzec zmierzono w tej sesji siedem razy.

### Sprostowanie własnego pomiaru

Pierwszy odczyt kodu wyjścia przy M-W8-8 zapisano jako **`KOD WYJSCIA: 0`**. To był pomiar
**statusu `grep`** w potoku, nie strażnika — a drugi przebieg szedł już na bazie z kotwicą
zapisaną przez przebieg pierwszy, więc naprawdę był zielony. Powtórzony pomiar bez potoku
i na wyczyszczonej tabeli `stan_konta`: **`KOD PRZY MUTACJI: 2`**.

### Znalezisko po drodze: strażnik oślepiony sekwencją `/*` w komentarzu liniowym

Pierwsza wersja nagłówka `kotwica.tsx` cytowała komendę zawierającą `makiety/*.dc.html`.
`pomocnicze.bez_komentarzy` zdejmuje komentarze blokowe wyrażeniem `/\*.*?\*/`, więc ciąg
`/*` w środku komentarza `//` **otworzył komentarz blokowy** i zjadł 90% pliku. Skutek:
pięć strażników W8 zaczerwieniło się na kodzie, który był poprawny. Zdanie przepisane bez
tej sekwencji. Wada jest w treści komentarza, nie w strażniku — ale pokazuje, że narzędzie
czyszczące kod potrafi oślepić pomiar, a wynik wygląda wtedy jak defekt kodu.

### Znalezisko z OGLĄDANIA EKRANU, którego nie złapał żaden test

Pole `<input type="date">` rysuje sobie przeglądarka według ustawień systemu. Na tym laptopie
data **2 września 2026** wyświetliła się jako **`09/02/2026`** — zapis, który po polsku czyta
się jako **9 lutego**. Pomyłka o siedem miesięcy przesuwa punkt startu całej prognozy i nie
zostawia śladu. Pod polem dopisano tę samą datę słowami (`sformatujOdczyt`, ten sam nośnik,
którego używa nagłówek ekranu). Wykryte zrzutem ekranu, nie testem — jak w W7.

### Czego przebieg W8 NIE objął

- **Nie mierzono na wdrożeniu w chmurze** — wszystkie liczby z lokalnej budowy produkcyjnej.
  Wdrożenie prowadzi Eva.
- **Nie zbudowano wezwania „Odśwież stan konta"** z `TrzyStany.dc.html` — kontrakt nie niesie
  stanu świeżości odczytu. Dług ze strażnikiem i progiem:
  `test_wezwanie_ODSWIEZ_Z_RAMKI_NIE_MA_dzis_na_ekranie`.
- **Nie sprawdzono kontrolki czytnikiem ekranu ani przy wyłączonym JavaScript.**
- **Nie ma ramki dla rozwiniętej kontrolki** — układ pól powstał bez makiety (odstępstwo od §3.6).

---

## Przebieg 2026-08-29 — W9b, sześć tras ekranu Budżet

**Gdzie.** Kopia drzewa poza repozytorium
(`scratchpad/mutacje-W9b`), `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` czyszczone przed
każdym przebiegiem. Po ostatnim cofnięciu `diff -rq` kopii z repozytorium: **bez różnic**.

Kontrola przed mutacjami (`test_trasy_budzet` + `test_nosniki` + `test_trasy_bez_rachunku`
+ `test_kontrakt_dwa_nosniki` + `test_magazyn_budzet`): **212 passed**.

| # | Mutacja | Który test padł (po nazwie) | Klasa | Wynik |
|---|---|---|---|---|
| **M-W9b-1** | do spisu `api/trasy.py` dopisana `Trasa("DELETE", "/api/plan/{id}", "budzet", …)` | `test_nosniki.py::test_kosz_planu_KONCZY_regule_a_nie_kasuje` | treść | **czerwony** |
| **M-W9b-2** | `ekran_budzet.zakoncz_pozycje` woła `magazyn.usun_plan` zamiast `zakoncz_plan` | `test_trasy_budzet.py::test_ekran_budzetu_NIE_WOLA_usun_plan` · `::test_P1_ZAKONCZYC_pozycje_planu_HISTORIA_ZOSTAJE` | treść | **czerwony** |
| **M-W9b-3** | `pozycje_wykonania` obcina posortowaną listę do jednego wiersza (`[:1]`) | `test_trasy_budzet.py::test_kazda_z_szesciu_tras_ODPOWIADA_i_nie_niesie_liczby` · `::test_najwieksze_odchylenie_STOI_U_GORY` · `::test_wiersz_z_DWOMA_pozycjami_planu_NIE_MA_jednego_numeru` · `::test_procent_bez_planu_to_MYSLNIK_a_nie_zero` · `::test_pasek_postepu_NIE_WYCHODZI_poza_sto` | **liczność** | **czerwony** |
| **M-W9b-4** | `pozycje_planu` oddaje kwotę przez `str(float(...))` zamiast `napis_kwoty` | `test_trasy_budzet.py::test_kwota_z_ZEREM_NA_KONCU_nie_gubi_go_po_drodze` · `::test_P1_ZMIENIC_pozycje_planu_przez_PUT` · `::test_kopiuj_plan_PRZENOSI_pozycje_do_miesiaca_bez_planu` | treść | **czerwony** |
| **M-W9b-5** | z `api/trasy_budzet.py` usunięta cała trasa `POST /api/plan` | `test_trasy_bez_rachunku.py::test_straznik_widzi_DOKLADNIE_dwanascie_tras` · `test_trasy_budzet.py::test_kazda_z_szesciu_tras_ODPOWIADA_i_nie_niesie_liczby` · `::test_P1_USTAWIC_pozycje_planu_przez_POST` · `::test_zakonczenie_NIE_JEST_metoda_DELETE` · `::test_kwota_z_ZEREM_NA_KONCU_nie_gubi_go_po_drodze` | **liczność** | **czerwony** |
| **M-W9b-6** | odmowa rachunku rezerwy zwraca `Decimal("0.00")` zamiast `None` | `test_trasy_budzet.py::test_rezerwa_BEZ_FORMY_nie_jest_zerem_tylko_zdaniem` | treść | **czerwony** |
| **M-W9b-7** | `magazyn.kopiuj_plan` wraca do stanu sprzed naprawy (wiersze miesiąca zamiast pozycji obowiązujących) | `test_trasy_budzet.py::test_kopiuj_plan_NIE_DOKLADA_pozycji_ktore_juz_obowiazuja` · `::test_kopiuj_plan_PRZENOSI_pozycje_do_miesiaca_bez_planu` | treść | **czerwony** |
| **M-W9b-8** | z `interfejs/lib/kontrakt.ts` usunięte pole `DaneBudzetu.liczbaPozycjiPlanu` | `test_kontrakt_dwa_nosniki.py::test_nazwy_pol_sie_ZGADZAJA[DaneBudzetu]` · `::test_RAPORT_ile_pol_porownano_po_kazdej_stronie` | **liczność** | **czerwony** |

| **M-W9b-9** | z `ekran_budzet.ustaw_pozycje` zdjęte sprawdzenie kategorii **przed** zapisem | `test_trasy_budzet.py::test_pozycja_planu_BEZ_KATEGORII_nie_dociera_do_bazy` · `::test_pozycja_planu_W_ZLYM_TYPIE_jest_odmowa` | treść | **czerwony** |
| **M-W9b-10** | `magazyn.ustal_regule_planu` zawsze traktuje pozycję jak nową (`obowiazujaca = None`) — utrata idempotencji | `test_trasy_budzet.py::test_ZAPIS_POWTORZONY_daje_jeden_skutek_a_nie_dwa` · `::test_P1_ZMIENIC_pozycje_planu_przez_PUT` · `::test_kazda_z_szesciu_tras_ODPOWIADA_i_nie_niesie_liczby` | treść | **czerwony** |

Kontrola po cofnięciu wszystkich ośmiu: **212 passed**. Po dołożeniu dwóch strażników
wejścia i idempotencji (M-9, M-10) kontrola powtórzona: **215 passed**, a `diff -rq` kopii
z repozytorium — **bez różnic**.

### Dwie klasy mutacji, bo jedna nie wystarcza

Ostrzeżenie z tej samej sesji (W7): mutacja kasująca trasę dowodzi tylko, że strażnik **znajduje
zepsutą rzecz** — nie że **wie, ile rzeczy zobaczył**. Dlatego trzy z ośmiu mutacji są
**licznościowe** (M-3 okraja listę wierszy, M-5 zabiera całą trasę, M-8 zabiera pole kontraktu),
a pięć jest **treściowych**. Gdyby istniały tylko treściowe, obchód odpowiedzi po pustym drzewie
i asercja „nie ma tu liczby zmiennoprzecinkowej" byłyby zielone przy odpowiedzi, która nie niesie
nic.

### Wada pieniężna znaleziona po drodze — `magazyn.kopiuj_plan` (M-W9b-7)

**Nie jest to wada wprowadzona w W9b.** Powstała w Z42, gdy pozycja planu stała się **regułą**
obowiązującą od swojego miesiąca do odwołania, a `kopiuj_plan` dalej czytał **wiersze** miesiąca
źródłowego. W9b jest pierwszym zadaniem, które wystawia tę funkcję na HTTP (`POST /api/plan/kopiuj`),
więc wada przestała być teoretyczna.

Pomiar przez trasę, 2026-08-29, przed naprawą — plan października złożony z trzech reguł
(Kredyty „Alior" 1 305,05 zł, Kredyty „Revolut" 319,76 zł, Czesne 660,00 zł):

```
LISTOPAD PRZED: [('Czesne','',660.00,d.25), ('Kredyty','Alior',1305.05,d.1), ('Kredyty','Revolut',319.76,d.12)]  plan 2284.81
WYNIK:          skopiowane 2, pominiete 1
LISTOPAD PO:    [('Czesne','',660.00,BRAK DNIA), ('Kredyty','',1305.05,BRAK DNIA),
                 ('Kredyty','Alior',1305.05,d.1), ('Kredyty','Revolut',319.76,d.12)]  plan 3589.86
```

Plan listopada urósł o **1 305,05 zł**, których nikt nie zaplanował, pojawiła się druga pozycja
„Kredyty" z pustą nazwą, a „Czesne" straciło dzień płatności — i wszystko to zwróciło meldunek
sukcesu. Trzy przyczyny naraz: (a) źródło czytane po wierszach, nie przez `budzet.plan_na_miesiac`;
(b) sprawdzenie „czy już jest" pomijało `opis`, więc kategoria z dwiema pozycjami zwijała się do
jednej; (c) kopia gubiła `opis`, `dzien`, `powtarzalna` i `co_ile_miesiecy`.

Naprawione: źródło i cel czyta ten sam nośnik co ekran, tożsamość to pełna trójka
(typ, kategoria, opis), granice okresu nie są kopiowane. Cztery istniejące strażniki
`test_magazyn_budzet.py` przeszły bez zmian; dołożono dwa nowe, oba z mutacją (M-W9b-7).

### Czego przebieg W9b NIE objął

- **Nie zbudowano ekranu.** Trasy i kontrakt — tak; interfejs Budżetu to zadanie Jacka.
  Bramka odwzorowania (`PRD` §12.7) dla `Budzet.dc.html` **nie była uruchamiana**.
- **Nie ma strażnika behawioralnego czytającego liczbę z wyrenderowanej strony** — luka ta sama,
  co opisana w `conftest.py` przy niezaniesionym `test_ekran_playwright.py`.
- **Nie sprawdzono zachowania na wdrożeniu w chmurze** — wszystkie liczby z przebiegu lokalnego
  przez `TestClient`. Wdrożenie prowadzi Eva.
- **Nie ruszono `magazyn.usun_plan` ani `magazyn.usun_cel`** — obie funkcje żyją w silniku
  i pozostają świadomie odcięte od warstwy sieciowej (Z-9).
- **Kontrolka „Wybrany miesiąc"** z ramki jest poza zakresem (rozstrzygnięcie Mili, §7 spisu
  `docs/2026-08-29-spis-ekran-budzet.md`) — trasa `GET /api/budzet` przyjmuje **jeden** parametr
  miesiąca.
