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
