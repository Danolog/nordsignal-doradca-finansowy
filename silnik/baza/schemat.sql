-- SCHEMAT BAZY — PostgreSQL. JEDYNY nosnik schematu (od W4, 2026-08-29).
--
-- TEN PLIK NIE JEST CALYM SCHEMATEM I TO JEST DECYZJA, NIE UBYTEK.
-- Niesie TRZYNASCIE tabel. Czternasta — `rejestr_stawek` — mieszka w
-- `wiedza/rejestr.py` (`SCHEMAT`, dialekt PostgreSQL), bo tam mieszka regula
-- "silnik czyta wylacznie stawki zatwierdzone przez czlowieka" (CLAUDE.md
-- §3.3/§3.4). Przepisanie jej tutaj byloby DRUGIM NOSNIKIEM liczb z ustaw.
-- Pelny napis DDL sklada `silnik.baza.schemat_postgresql()`.
-- NIGDY nie stawiaj bazy z samego tego pliku: rejestr zostanie pusty,
-- a aplikacja nie ma skad wziac ani jednej stawki.
--
-- TRZY ZMIANY TYPOW WOBEC POPRZEDNIKA, wszystkie w jedna strone — mniej obejsc:
--   kwota TEXT   -> NUMERIC(14,2)  (poprzednik nie mial typu dziesietnego)
--   data  TEXT   -> DATE           (koniec porownan dat na napisach)
--   flaga INTEGER-> BOOLEAN        (koniec pytania "czy 0 znaczy nie, czy brak")
--
-- ZGODNOSC Z BAZA JEST PILNOWANA, NIE ZAKLADANA:
-- `testy/test_schemat_wobec_bazy.py` stawia baze z tego napisu i porownuje
-- go z katalogiem systemowym serwera kolumna po kolumnie — typ,
-- obowiazkowosc, dziedzina wartosci, wiezy jednoznacznosci, indeksy.
-- Blad skladni czerwieni sie tam w fiksturze, a nie przechodzi po cichu.

-- ── wersja schematu ───────────────────────────────────────────────────────
-- NASTEPCA `PRAGMA user_version` (W4, 2026-08-29). SQLite trzymal wersje
-- schematu w naglowku PLIKU bazy; PostgreSQL pliku nie ma, wiec liczba musi
-- gdzies zamieszkac. Tutaj, a NIE w osobnym module migracji, bo baza
-- postawiona z `schemat_postgresql()` ma byc kompletna — tabela wersji
-- dolozona obok byla by dokladnie ta klasa przeoczenia, ktora daje
-- "migracja przeszla, tylko rejestr pusty".
--
-- JEDEN WIERSZ, WYMUSZONY WIEZEM. Kolumna `jedyny` przyjmuje wylacznie
-- wartosc prawda i jest kluczem glownym, wiec drugiego wiersza nie da sie
-- wpisac. Dwa wiersze znaczylyby dwie odpowiedzi na pytanie "w jakiej wersji
-- jest ta baza", a `_wersja_bazy` musialby miedzy nimi wybierac.
CREATE TABLE IF NOT EXISTS wersja_schematu (
    jedyny BOOLEAN PRIMARY KEY DEFAULT TRUE,
    wersja INT NOT NULL,
    CONSTRAINT naprawde_jedyny CHECK (jedyny)
);

-- ── slownik kategorii ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kategorie (
    id          BIGSERIAL PRIMARY KEY,
    typ         TEXT    NOT NULL,
    nazwa       TEXT    NOT NULL,
    kolejnosc   INT     NOT NULL DEFAULT 0,
    aktywna     BOOLEAN NOT NULL DEFAULT TRUE,
    -- `systemowa` NIE MA TU KOLUMNY i to jest decyzja (2026-08-29, W1).
    -- To wlasnosc SLOWNIKA STARTOWEGO, nie stan wiersza: wylicza ja
    -- `silnik/ekran_ksiegowanie.py` z `budzet.KATEGORIE_SPOZA_ARKUSZA`.
    -- Kolumna w bazie byla by drugim nosnikiem tej samej reguly — i pierwsza,
    -- ktora sie rozjedzie, bo nikt jej nie zapisuje.
    -- NOWE (PRD §6.3 p.1): czy kategoria liczy sie do progu poduszki.
    -- Bez tego prog poduszki jest PRZEDZIALEM 29 651–63 649 zl, nie liczba.
    -- NULL znaczy "Darek jeszcze nie rozstrzygnal" — i to jest stan rozny
    -- od "nie jest niezbedna". Aplikacja ma o tym mowic, nie zgadywac.
    niezbedna   BOOLEAN,
    UNIQUE (typ, nazwa),
    CONSTRAINT typ_znany CHECK (typ IN ('Przychody','Wydatki','Oszczędności'))
);

-- ── wpisy faktyczne ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wpisy_budzetu (
    id          BIGSERIAL PRIMARY KEY,
    data        DATE          NOT NULL,
    typ         TEXT          NOT NULL,
    kategoria   TEXT          NOT NULL,
    kwota       NUMERIC(14,2) NOT NULL,
    szczegoly   TEXT          NOT NULL DEFAULT '',
    -- NOWE (PRD §6.3 p.2): skad wpis pochodzi. To jest BRAMKA POPRAWNOSCI,
    -- nie metadana dla porzadku. Bez niej "wgrac historie 2025" i "nie liczyc
    -- jej do podatku 2026" sa dwiema regulami w dwoch miejscach, ktore
    -- rozjada sie przy pierwszej zmianie. Z nia jest JEDNA regula w jednym
    -- miejscu: do rachunku wchodza wylacznie wiersze o zrodle 'recznie'.
    zrodlo      TEXT          NOT NULL DEFAULT 'recznie',
    CONSTRAINT kwota_bez_znaku CHECK (kwota >= 0),
    CONSTRAINT zrodlo_znane CHECK (zrodlo IN ('recznie','historia-2025','import'))
);
CREATE INDEX IF NOT EXISTS wpisy_po_dacie ON wpisy_budzetu (data);
CREATE INDEX IF NOT EXISTS wpisy_do_rachunku ON wpisy_budzetu (data) WHERE zrodlo <> 'historia-2025';

-- ── plan budzetu ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plan_budzetu (
    id              BIGSERIAL PRIMARY KEY,
    rok             INT           NOT NULL,
    miesiac         INT           NOT NULL,
    typ             TEXT          NOT NULL,
    kategoria       TEXT          NOT NULL,
    kwota_planowana NUMERIC(14,2) NOT NULL,
    powtarzalna     BOOLEAN       NOT NULL DEFAULT FALSE,
    do_roku         INT,
    do_miesiaca     INT,
    opis            TEXT          NOT NULL DEFAULT '',
    dzien           INT,
    co_ile_miesiecy INT           NOT NULL DEFAULT 1,
    UNIQUE (rok, miesiac, typ, kategoria, opis),
    CONSTRAINT miesiac_sensowny CHECK (miesiac BETWEEN 1 AND 12),
    CONSTRAINT dzien_sensowny CHECK (dzien IS NULL OR dzien BETWEEN 1 AND 31)
);

-- ── dzialalnosc gospodarcza ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS przychody_jdg (
    id             BIGSERIAL PRIMARY KEY,
    -- WIEZ Z NAZWA WLASNA (W4). Bez `CONSTRAINT ...` PostgreSQL nadalby mu
    -- nazwe automatyczna `przychody_jdg_numer_faktury_key`, w ktorej
    -- przypadkiem siedzi napis "numer_faktury" — i dawne dopasowanie po
    -- TRESCI komunikatu sterownika przezylo by migracje PRZYPADKIEM, wiszac
    -- na nazwie, ktorej nikt nie wybral. Teraz `magazyn._zapisz` rozpoznaje
    -- naruszenie po `e.diag.constraint_name` rownym tej nazwie.
    numer_faktury  TEXT          NOT NULL,
    CONSTRAINT numer_faktury_niepowtarzalny UNIQUE (numer_faktury),
    data           DATE          NOT NULL,   -- data WYSTAWIENIA
    data_zaplaty   DATE,
    kwota_netto    NUMERIC(14,2) NOT NULL,
    stawka_vat     NUMERIC(6,4)  NOT NULL,
    kwota_vat      NUMERIC(14,2) NOT NULL,
    -- NOWE (PRD §6.3 p.3, decyzja D-35): VAT liczy sie MEMORIALOWO —
    -- obowiazek powstaje z chwila WYSTAWIENIA faktury, nie jej zaplaty.
    -- Faktura wystawiona 5 X za wrzesien nalezy do okresu PAZDZIERNIK,
    -- termin 25 XI. Poprzednia aplikacja sumowala VAT ze WSZYSTKICH faktur
    -- bez wzgledu na okres — kwota siedziala w zlym miesiacu.
    -- BEZ `NOT NULL` — i to jest decyzja W1 (2026-08-29), nie przeoczenie.
    -- `zapisz_fakture` tej kolumny NIE WYPELNIA, bo data domyslna byla by
    -- ZMYSLENIEM daty powstania obowiazku podatkowego (nosnik decyzji:
    -- `testy/test_trzy_kolumny.py::test_data_obowiazku_vat_startuje_pusta_a_nie_zgadnieta`).
    -- Wiez `NOT NULL` nie wymuszal by tu daty — odrzucal by KAZDY zapis
    -- faktury, co do jednego. NULL znaczy "nie wiem".
    -- PROG POWROTU WIEZU: pierwszy pisarz, ktory te date wyliczy.
    data_obowiazku_vat DATE,
    -- BEZ `DEFAULT ''` (W1). `_wymagaj_pkwiu` odrzuca pusty napis powolujac
    -- sie na art. 12 ust. 3, wiec wartosc domyslna jest dziura obok drogi
    -- sprawdzanej: pozwala wstawic wiersz, ktorego pisarz nigdy by nie zapisal.
    pkwiu          TEXT          NOT NULL,
    -- CZTERY KOLUMNY POLICZONE PRZY WYSTAWIENIU FAKTURY (W1, 2026-08-29).
    -- Nie byly tu wczesniej, a `zapisz_fakture` (`magazyn.py:835`) zapisuje
    -- je od poczatku — postawienie bazy z poprzedniej wersji tego pliku
    -- wywracalo by KAZDY zapis faktury na nieznanej kolumnie.
    --
    -- `stawka_ryczaltu` — ULAMEK, ta sama jednostka co `stawka_vat`.
    --   UWAGA, TO JEST TA KOLUMNA: dzis NIKT JEJ NIE CZYTA. Wszystkie
    --   odczyty `stawka_ryczaltu` w silniku ida z `forma_opodatkowania`,
    --   nie stad. Jej ISTNIENIE nie jest wada — wada byloby liczenie z niej
    --   czegokolwiek DOMYSLNIE, bo Darek jest na SKALI (CLAUDE.md §2).
    --   Zostaje jako slad, czym policzono te konkretna fakture.
    --   BEZ `NOT NULL` (W4, 2026-08-29) — dlug odlozony imiennie do tego
    --   zadania. Kolumna byla obowiazkowa przy pisarzu, ktory nie ma jej skad
    --   wziac: Darek jest na SKALI (CLAUDE.md §2), a przy skali stawka
    --   ryczaltu nie istnieje. Jedyna droga do spelnienia wiezu bylo wpisanie
    --   ZERA — czyli odpowiedzi, ktorej nikt nie udzielil, nieodrozninalnej
    --   od ryczaltu 0%. NULL znaczy "nie dotyczy: ta faktura nie zostala
    --   policzona ryczaltem". To ta sama regula, co w
    --   `forma_opodatkowania.stawka_ryczaltu`.
    stawka_ryczaltu NUMERIC(6,4),
    -- `zaplacony_zus` — czytana: `magazyn.czy_skladki_naliczone_w_miesiacu`,
    --   `narzedzia` (suma skladek), `podatki.ryczalt_z_faktury`.
    zaplacony_zus  NUMERIC(14,2) NOT NULL,
    -- `zysk_netto` — czytana: `narzedzia` (co zostaje), `podatki`.
    zysk_netto     NUMERIC(14,2) NOT NULL,
    -- `stawki_wersja` — slad audytowy: ktora wersja rejestru stawek dala te
    --   liczby. Dzis bez czytelnika, i to jest w porzadku: sladu nie czyta
    --   sie codziennie, czyta sie go, gdy kwota okaze sie sporna.
    stawki_wersja  TEXT          NOT NULL,
    wpis_budzetu_id BIGINT REFERENCES wpisy_budzetu(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS koszty_jdg (
    id              BIGSERIAL PRIMARY KEY,
    data            DATE          NOT NULL,
    opis            TEXT          NOT NULL,
    kwota_netto     NUMERIC(14,2) NOT NULL,
    kwota_vat       NUMERIC(14,2) NOT NULL,
    wpis_budzetu_id BIGINT REFERENCES wpisy_budzetu(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS godziny (
    id               BIGSERIAL PRIMARY KEY,
    data             DATE          NOT NULL,
    rodzaj_czynnosci TEXT          NOT NULL,
    liczba_godzin    NUMERIC(8,2)  NOT NULL,
    opis             TEXT          NOT NULL DEFAULT '',
    -- PKWiU zostaje w schemacie, ale SCHODZI Z EKRANU (D-25): przy skali
    -- jedna stawka od calosci dochodu, wiec rozdzielanie czynnosci nie sluzy
    -- kwalifikacji. Kolumny nie kasujemy — sluzy porownaniu form.
    -- BEZ `DEFAULT ''` (W1) — z tego samego powodu co w `przychody_jdg`:
    -- `_wymagaj_pkwiu` odrzuca pusty napis, wiec wartosc domyslna byla by
    -- obejsciem wlasnej reguly.
    pkwiu            TEXT          NOT NULL
);

-- ── majatek i dlugi ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS majatek (
    id           BIGSERIAL PRIMARY KEY,
    nazwa_aktywa TEXT          NOT NULL,
    kategoria    TEXT          NOT NULL,
    wartosc      NUMERIC(14,2) NOT NULL
);
-- Rachunek rozliczeniowy MOZE BYC TYLKO JEDEN (D-30): to ten, z ktorego ida
-- wydatki, i jego saldo wola kotwica prognozy. Dwa takie wiersze znaczylyby,
-- ze aplikacja nie wie, ktore saldo jest tym wlasciwym.
CREATE UNIQUE INDEX IF NOT EXISTS majatek_jeden_rozliczeniowy
    ON majatek ((kategoria)) WHERE kategoria = 'rachunek rozliczeniowy';

CREATE TABLE IF NOT EXISTS zobowiazania (
    id             BIGSERIAL PRIMARY KEY,
    nazwa          TEXT          NOT NULL,
    kapital        NUMERIC(14,2) NOT NULL,
    rata_minimalna NUMERIC(14,2) NOT NULL,
    -- JEDNOSTKA: PROCENT. 9 znaczy 9%. To jest rozjazd z `stawka_ryczaltu`,
    -- ktora trzyma ULAMEK — swiadomy, bo tak Darek podaje w formularzu.
    -- Pomnozenie kapitalu przez 9 zamiast 0,09 to blad stukrotny.
    -- NULL znaczy "nie wiem", 0 znaczy "zero procent" — to dwa rozne stany.
    oprocentowanie NUMERIC(6,3),
    CONSTRAINT oprocentowanie_sensowne CHECK (
        oprocentowanie IS NULL OR (oprocentowanie >= 0 AND oprocentowanie <= 100)
    )
);

-- ── plynnosc ──────────────────────────────────────────────────────────────
-- Kotwica prognozy. ZRODLEM JEST ODCZYT, majatek go wola (D-28/D10).
-- Kotwica NIGDY nie jest suma sald: odczyt niesie DATE, majatek nie —
-- wyprowadzenie kotwicy z majatku kazaloby date zmyslic, a prognoza
-- udawalaby swiezosc kazdego dnia bez nowego odczytu.
CREATE TABLE IF NOT EXISTS stan_konta (
    data  DATE PRIMARY KEY,
    kwota NUMERIC(14,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS cele_oszczednosciowe (
    id             BIGSERIAL PRIMARY KEY,
    nazwa          TEXT          NOT NULL UNIQUE,
    kategoria      TEXT          NOT NULL,
    kwota_docelowa NUMERIC(14,2) NOT NULL,
    -- `NOT NULL` (W1, 2026-08-29). `zapisz_cel` przyjmuje `termin: date`
    -- jako argument obowiazkowy i wola na nim `.isoformat()` — droga do
    -- zapisania celu bez terminu nie istnieje. Kolumna dopuszczajaca NULL
    -- obiecywala stan, ktorego aplikacja nie potrafi wytworzyc.
    termin         DATE          NOT NULL
    -- `nadpisana_recznie` NIE MA TU KOLUMNY (W1). PRD §10.3 S-2 zapowiada
    -- prog poduszki liczony z mozliwoscia nadpisania, ale dzis nie istnieje
    -- ani pisarz, ani czytelnik tej flagi. Kolumna bez obu jest obietnica
    -- w ksztalcie danych: przy migracji przyjdzie pusta i bedzie wygladac
    -- jak odpowiedz "nie nadpisano" na pytanie, ktorego nikt nie zadal.
    -- PROG POWROTU: razem z pisarzem, czyli przy wdrozeniu S-2.
);

-- ── nastawy ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS forma_opodatkowania (
    rok             INT PRIMARY KEY,
    forma           TEXT NOT NULL,
    stawka_ryczaltu NUMERIC(6,4),   -- ULAMEK. Wypelniona TYLKO przy ryczalcie.
    -- BEZ 'LINIOWY' (W1, 2026-08-29). `magazyn.forma_na_rok` ODRZUCA kazda
    -- forme spoza `magazyn.FORMY_ZAPISYWALNE` = ('SKALA','RYCZALT'), a
    -- `zapisz_forme` nie potrafi jej nawet zapisac. Dziedzina szersza od
    -- tego, co rachunek obsluguje, to ten sam mechanizm wady, ktory
    -- w poprzedniej aplikacji dawal kwoty liczone forma, ktorej Darek nie ma:
    -- baza dopuszcza stan, na ktorym silnik wybucha.
    -- Podatek liniowy ZOSTAJE jako opcja POROWNANIA form
    -- (`stawki.STAWKA_ZDROWOTNEJ_LINIOWY`) — porownanie nic nie zapisuje.
    -- Ta lista jest SWIADOMYM drugim nosnikiem `FORMY_ZAPISYWALNE`; pilnuje
    -- jej `test_dziedzina_formy_ZGADZA_SIE_z_FORMY_ZAPISYWALNE`.
    CONSTRAINT forma_znana CHECK (forma IN ('SKALA','RYCZALT')),
    -- Stawka ryczaltu przy skali jest sprzecznoscia, a nie pustym polem.
    -- To jest ta sama klasa wady, ktora w poprzedniej aplikacji dawala
    -- kwoty liczone forma, ktorej Darek nie ma.
    CONSTRAINT stawka_tylko_przy_ryczalcie CHECK (
        (forma = 'RYCZALT' AND stawka_ryczaltu IS NOT NULL)
        OR (forma <> 'RYCZALT' AND stawka_ryczaltu IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS ustawienia (
    klucz   TEXT PRIMARY KEY,
    wartosc TEXT NOT NULL
);

-- ── cichy straznik ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS przebiegi_straznika (
    id                    BIGSERIAL PRIMARY KEY,
    -- BEZ `DEFAULT now()` (W1). `magazyn.zapisz_przebieg_straznika` podaje
    -- `kiedy` zawsze i jawnie. Wartosc domyslna byla by drugim nosnikiem
    -- odpowiedzi "kiedy strażnik biegl" — i przy przenoszeniu wierszy
    -- z SQLite ostemplowala by je godzina MIGRACJI zamiast godzina przebiegu.
    kiedy                 TIMESTAMPTZ NOT NULL,
    stan_prognozy         TEXT        NOT NULL,
    pierwszy_dzien_ujemny DATE,
    pilnych               INT         NOT NULL,
    powod                 TEXT,
    zrodla                TEXT        NOT NULL,
    komunikat             TEXT        NOT NULL,
    powiadomiono          BOOLEAN     NOT NULL DEFAULT FALSE
);
