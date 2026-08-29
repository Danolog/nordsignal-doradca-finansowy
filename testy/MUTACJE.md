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
