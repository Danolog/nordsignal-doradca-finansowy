"""Oś terminów — czysta arytmetyka nad wynikiem prognozy (Z72)."""

from datetime import date
from decimal import Decimal

from silnik.rdzen import co_mnie_czeka, prognoza_plynnosci as pp


def _dzien(data, saldo, zdarzenia=(), saldo_realne=None):
    """Domyślnie OBIE linie równe — tak jest w większości przypadków testowych.

    `saldo_realne` podaje się jawnie tylko tam, gdzie linie mają się
    rozjechać; bez rozjazdu żaden test nie odróżni, którą z nich czyta kod.
    """
    return pp.Dzien(
        data=data, saldo_ostrozne=Decimal(saldo),
        saldo_realne=Decimal(saldo if saldo_realne is None else saldo_realne),
        zdarzenia=tuple(zdarzenia))


def _zdarzenie(nazwa, kwota, rodzaj=pp.RODZAJ_DANINA, domniemany=False):
    return pp.Zdarzenie(nazwa=nazwa, rodzaj=rodzaj,
                        kwota_ostrozna=Decimal(kwota), kwota_realna=Decimal(kwota),
                        dzien_domniemany=domniemany)


def _prognoza(dni, **nadpisz):
    return pp.Prognoza(stan=pp.STAN_POLICZONA, dni=tuple(dni),
                       daniny_policzone=True, **nadpisz)


def test_pozycje_biora_kwote_i_date_Z_PROGNOZY_bez_wlasnego_rachunku():
    prognoza = _prognoza([
        _dzien(date(2026, 9, 20), "500.00",
               [_zdarzenie("ZUS", "-1926.76")]),
        _dzien(date(2026, 9, 25), "300.00",
               [_zdarzenie("VAT", "-200.00")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert [p.nazwa for p in wynik.pozycje] == ["ZUS", "VAT"]
    assert wynik.pozycje[0].kwota == Decimal("-1926.76")
    assert wynik.pozycje[0].saldo_po == Decimal("500.00")
    assert wynik.pozycje[0].dni_do == 2


def test_WPLYWY_nie_trafiaja_na_os_terminow():
    """Oś odpowiada na pytanie 'co mnie czeka do zapłacenia'. Przychód JDG
    na tej liście czytałby się jak zobowiązanie.

    To strażnik filtru RODZAJU. Filtr ZNAKU ma własnego strażnika niżej —
    patrz `test_DODATNIA_kwota_rodzaju_wyplywu_tez_nie_trafia_na_os`.

    Kontrola LICZNOŚCI (specyfikacja §7.4, znalezisko Leo W3): dzień niesie
    DWA zdarzenia — jedno, które ma odpaść, i jedno, które MA trafić na oś.
    Asercja na samym braku przeszłaby także wtedy, gdyby pętla po
    `prognoza.dni` przestała działać w ogóle albo gdyby okno odcięło ten
    dzień — czyli dowodziłaby, że filtr działa, nie zobaczywszy go ani raz.
    Lista nazw zamiast pustki mówi, że pomiar czegoś DOTARŁ.
    """
    prognoza = _prognoza([
        _dzien(date(2026, 9, 30), "9000.00",
               [_zdarzenie("Przychód JDG", "8400.00", pp.RODZAJ_PRZYCHOD_JDG),
                _zdarzenie("ZUS", "-1926.76")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert [p.nazwa for p in wynik.pozycje] == ["ZUS"]
    assert wynik.najblizszy_wyplyw == date(2026, 9, 30)


def test_DODATNIA_kwota_rodzaju_wyplywu_tez_nie_trafia_na_os():
    """Strażnik ZNAKU, osobny od strażnika RODZAJU (decyzja Olivera R-1).

    Plan zakładał, że usunięcie sprawdzenia znaku zaczerwieni
    `test_WPLYWY_nie_trafiaja_na_os_terminow`. Nie zaczerwieni: tamten test
    używa rodzaju `przychod_jdg`, który odpada już na filtrze RODZAJU, więc
    filtr ZNAKU nie jest tam w ogóle wykonywany. Bez tego testu drugi filtr
    nie miałby żadnego strażnika — a wyglądałby na pilnowany.

    Zdarzenie o rodzaju wypływu, ale z kwotą dodatnią — na przykład zwrot
    podatku wpisany do planu — nie jest rzeczą do zapłacenia i na osi „co
    mnie czeka" czytałoby się jak zobowiązanie.

    Kontrola LICZNOŚCI (specyfikacja §7.4, znalezisko Leo W3): dzień niesie
    DWA zdarzenia — jedno, które ma odpaść, i jedno, które MA trafić na oś.
    Asercja na samym braku przeszłaby także wtedy, gdyby pętla po
    `prognoza.dni` przestała działać w ogóle albo gdyby okno odcięło ten
    dzień — czyli dowodziłaby, że filtr działa, nie zobaczywszy go ani raz.
    Lista nazw zamiast pustki mówi, że pomiar czegoś DOTARŁ.
    """
    prognoza = _prognoza([
        _dzien(date(2026, 9, 30), "9000.00",
               [_zdarzenie("Zwrot podatku", "500.00", pp.RODZAJ_PLAN),
                _zdarzenie("ZUS", "-1926.76")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert [p.nazwa for p in wynik.pozycje] == ["ZUS"]
    assert wynik.najblizszy_wyplyw == date(2026, 9, 30)


def test_UJEMNE_zdarzenie_spoza_rodzajow_wyplywu_tez_nie_trafia_na_os():
    """Drugie znalezisko z przebiegu mutacyjnego Z72: usunięcie filtru
    RODZAJU przeżyło całą suitę (850 zielonych).

    Powód jest ten sam, co przy filtrze ZNAKU, tylko odwrócony:
    `test_WPLYWY_nie_trafiaja_na_os_terminow` podaje przychód z kwotą
    DODATNIĄ, więc odsiewa go filtr ZNAKU — a filtr RODZAJU mógł zniknąć
    bez śladu. Dwa filtry, jeden strażnik, i to nie ten, o którym myśleliśmy.

    Tutaj zdarzenie ma rodzaj SPOZA `RODZAJE_WYPLYWU` i kwotę UJEMNĄ —
    czyli korektę przychodu w dół. Filtr znaku jej nie zatrzyma; jeżeli
    zatrzyma ją cokolwiek, to wyłącznie filtr rodzaju. Korekta przychodu
    nie jest rzeczą do zapłacenia i na osi „co mnie czeka" byłaby długiem,
    którego nikt nie ma.

    Kontrola LICZNOŚCI (specyfikacja §7.4, znalezisko Leo W3): dzień niesie
    DWA zdarzenia — jedno, które ma odpaść, i jedno, które MA trafić na oś.
    Asercja na samym braku przeszłaby także wtedy, gdyby pętla po
    `prognoza.dni` przestała działać w ogóle albo gdyby okno odcięło ten
    dzień — czyli dowodziłaby, że filtr działa, nie zobaczywszy go ani raz.
    Lista nazw zamiast pustki mówi, że pomiar czegoś DOTARŁ.
    """
    prognoza = _prognoza([
        _dzien(date(2026, 9, 30), "9000.00",
               [_zdarzenie("Korekta faktury", "-1200.00",
                           pp.RODZAJ_PRZYCHOD_JDG),
                _zdarzenie("ZUS", "-1926.76")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert [p.nazwa for p in wynik.pozycje] == ["ZUS"]
    assert wynik.najblizszy_wyplyw == date(2026, 9, 30)
    assert wynik.pilnych == 0


def test_okno_odcina_to_co_ZA_DALEKO_i_to_co_MINELO():
    prognoza = _prognoza([
        _dzien(date(2026, 9, 1), "100.00", [_zdarzenie("Stare", "-10.00")]),
        _dzien(date(2026, 9, 20), "100.00", [_zdarzenie("W oknie", "-10.00")]),
        _dzien(date(2026, 12, 1), "100.00", [_zdarzenie("Daleko", "-10.00")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18), okno_dni=45)
    assert [p.nazwa for p in wynik.pozycje] == ["W oknie"]


def test_PILNA_wymaga_TRZECH_warunkow_naraz():
    """Termin blisko i saldo pod kreską — jedno bez drugiego nie jest
    pilnością. Kontrola dwustronna na wszystkich trzech członach."""
    assert co_mnie_czeka.pilna(kwota=Decimal("-100"), saldo_po=Decimal("-1"),
                               dni_do=1) is True
    # saldo dodatnie: pieniądze są, termin nieistotny
    assert co_mnie_czeka.pilna(kwota=Decimal("-100"), saldo_po=Decimal("1"),
                               dni_do=1) is False
    # daleki termin: jest czas zareagować
    assert co_mnie_czeka.pilna(kwota=Decimal("-100"), saldo_po=Decimal("-1"),
                               dni_do=30) is False
    # wpływ: nie ma czego płacić
    assert co_mnie_czeka.pilna(kwota=Decimal("100"), saldo_po=Decimal("-1"),
                               dni_do=1) is False


def test_licznik_pilnych_zgadza_sie_z_LISTA_pozycji():
    """Kontrola liczności: licznik liczony osobno od listy rozjedzie się
    po cichu przy pierwszej zmianie reguły."""
    prognoza = _prognoza([
        _dzien(date(2026, 9, 19), "-50.00", [_zdarzenie("ZUS", "-1926.76")]),
        _dzien(date(2026, 9, 20), "-90.00", [_zdarzenie("VAT", "-40.00")]),
        _dzien(date(2026, 10, 20), "-90.00", [_zdarzenie("PIT", "-40.00")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pilnych == sum(1 for p in wynik.pozycje if p.pilna)
    assert wynik.pilnych == 2, [(p.nazwa, p.dni_do, p.pilna) for p in wynik.pozycje]


def test_saldo_po_niesie_linie_OSTROZNA_a_nie_realna():
    """Znalezisko z przebiegu mutacyjnego Z72: mutacja M343 przeżyła.

    Plan przewidywał, że podmiana `saldo_po=dzien.saldo_ostrozne` na
    `dzien.saldo_realne` zaczerwieni `test_licznik_pilnych_zgadza_sie_z_LISTA
    _pozycji`. Nie zaczerwieniła — WSZYSTKIE dni w tamtym teście mają obie
    linie równe, więc żadna asercja nie potrafiła ich rozróżnić. Strażnik
    liczności był prawdziwy, ale linii nie pilnował nikt.

    Rozjazd linii jest tu jedynym elementem, który cokolwiek mierzy: linia
    ostrożna schodzi pod kreskę, realna zostaje nad nią. Ekran ma pokazać
    liczbę OSTROŻNĄ — pokazanie realnej znaczyłoby „pieniądze będą", gdy
    scenariusz ostrożny mówi, że ich nie będzie.

    Jeden strażnik na oba użycia linii ostrożnej w `zbuduj`: pole `saldo_po`
    (asercja o kwocie) i argument przekazywany do `pilna` (asercja o fladze).
    """
    prognoza = _prognoza([
        _dzien(date(2026, 9, 19), "-50.00",
               [_zdarzenie("ZUS", "-1926.76")], saldo_realne="900.00"),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pozycje[0].saldo_po == Decimal("-50.00")
    assert wynik.pozycje[0].pilna is True
    assert wynik.pilnych == 1


def test_prognoza_ktora_NIE_LICZYLA_daje_stan_nie_wiem_i_zero_pozycji():
    prognoza = pp.Prognoza(
        stan=pp.STAN_NIE_WIEM, dni=None,
        zastrzezenia=(pp.Zastrzezenie(pp.KOD_BRAK_KOTWICY, "Wpisz stan konta."),))
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.stan == pp.STAN_NIE_WIEM
    assert wynik.pozycje == ()
    assert wynik.zastrzezenia[0].kod == pp.KOD_BRAK_KOTWICY


def test_stan_NIEAKTUALNY_przechodzi_z_prognozy_a_nie_znika():
    prognoza = _prognoza([_dzien(date(2026, 9, 20), "100.00",
                                 [_zdarzenie("ZUS", "-10.00")])])
    prognoza = pp.Prognoza(stan=pp.STAN_NIEAKTUALNA, dni=prognoza.dni,
                           daniny_policzone=True)
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.stan == pp.STAN_NIEAKTUALNA
    assert len(wynik.pozycje) == 1


def test_zbieracz_czyta_baze_i_NIE_liczy_sam(tmp_path):
    """Ten sam rozdział co przy `podatki.rezerwa_z_bazy` i `prognozuj`:
    rachunek czysty, zbieranie osobno i cienkie."""
    from silnik.rdzen import magazyn

    polaczenie = magazyn.zmigruj_i_polacz()
    try:
        magazyn.zapisz_stan_konta(polaczenie, data=date(2026, 9, 1),
                                  kwota="5000.00")
        wynik = co_mnie_czeka.zestaw(polaczenie, dzis=date(2026, 9, 1))
    finally:
        polaczenie.close()
    assert wynik.stan in (pp.STAN_POLICZONA, pp.STAN_NIEAKTUALNA)
    assert wynik.rezerwa is not None, "zbieracz nie podał rezerwy"


def test_POWOD_powiadomienia_zapala_sie_na_liniach_ujemnej_i_na_pilnej():
    prognoza = _prognoza(
        [_dzien(date(2026, 9, 25), "-500.00", [_zdarzenie("VAT", "-600.00")])],
        pierwszy_dzien_ujemny=date(2026, 9, 25), brakuje=Decimal("500.00"))
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    powod = co_mnie_czeka.powod_powiadomienia(wynik, prognoza=prognoza,
                                              dzis=date(2026, 9, 18))
    assert powod is not None and "2026-09-25" in powod


def test_POWOD_MILCZY_gdy_zejscie_pod_kreske_jest_DALEKO():
    """Powiadomienie codzienne przestaje się czytać. Decyzja Darka
    2026-08-27: budzi wyłącznie pieniądze pod kreską, i to blisko."""
    prognoza = _prognoza(
        [_dzien(date(2026, 12, 1), "-500.00", [_zdarzenie("VAT", "-600.00")])],
        pierwszy_dzien_ujemny=date(2026, 12, 1), brakuje=Decimal("500.00"))
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert co_mnie_czeka.powod_powiadomienia(
        wynik, prognoza=prognoza, dzis=date(2026, 9, 18)) is None


def test_POWOD_MILCZY_gdy_prognoza_NIE_LICZYLA():
    """Brak wiedzy nie jest ostrzeżeniem — i nie jest spokojem. Strażnik
    ma o tym napisać na pasku, nie budzić systemu."""
    prognoza = pp.Prognoza(stan=pp.STAN_NIE_WIEM, dni=None)
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert co_mnie_czeka.powod_powiadomienia(
        wynik, prognoza=prognoza, dzis=date(2026, 9, 18)) is None


def test_POWOD_MILCZY_gdy_dni_sa_None_MIMO_zapamietanego_dnia_ujemnego():
    """Trzecie znalezisko z przebiegu mutacyjnego: mutacja M346 przeżyła.

    Plan przewidywał, że usunięcie `if prognoza.dni is None: return None`
    zaczerwieni `test_POWOD_MILCZY_gdy_prognoza_NIE_LICZYLA`. Nie zaczerwieni:
    tamten test podaje prognozę, w której `pierwszy_dzien_ujemny` też jest
    `None` i pozycji nie ma żadnych, więc funkcja wraca `None` **przez
    dalsze gałęzie**, nie przez strażnika. Strażnik wyglądał na pilnowany
    i nie pilnował niczego.

    Ten test wytwarza jedyny stan, w którym strażnik faktycznie coś robi:
    `dni is None` (nie liczyłem) obok NIEPUSTEGO `pierwszy_dzien_ujemny`
    — pola, które zostało z poprzedniego przebiegu. `prognoza_plynnosci.
    zbuduj` takiego wyniku dziś nie produkuje (gałąź „nie wiem" w linii 287
    zwraca tylko `stan`, `zastrzezenia` i horyzont), ale `powod_powiadomienia`
    dostaje prognozę OD WOŁAJĄCEGO i nie ma jak sprawdzić, skąd ona pochodzi.

    Reguła jest tu twarda i jednokierunkowa: `dni is None` znaczy „NIE
    LICZYŁEM" i **bije każde inne pole**. Brak wiedzy nie jest ostrzeżeniem
    ani spokojem — obudzenie systemu na podstawie liczby, której nikt w tym
    przebiegu nie policzył, jest dokładnie tą awarią, przed którą stoi
    reguła D11.
    """
    prognoza = pp.Prognoza(stan=pp.STAN_NIE_WIEM, dni=None,
                           pierwszy_dzien_ujemny=date(2026, 9, 20),
                           brakuje=Decimal("500.00"))
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pozycje == ()
    assert co_mnie_czeka.powod_powiadomienia(
        wynik, prognoza=prognoza, dzis=date(2026, 9, 18)) is None


def test_POWOD_przy_pozycji_pilnej_niesie_NAZWE_pozycji_a_NIE_zdania_o_linii():
    """Strażnik OSIĄGALNOŚCI gałęzi pierwszej — i kolejności obu gałęzi.

    Wejście jest tu w pełni SPÓJNE, w odróżnieniu od pierwszej wersji tego
    testu: `pierwszy_dzien_ujemny` wskazuje dokładnie ten dzień, w którym
    linia schodzi pod kreskę, czyli dokładnie to, co ustawiłby silnik.
    Oba wyzwalacze zachodzą więc JEDNOCZEŚNIE — i o to chodzi. Test mierzy
    nie „czy budzi", tylko KTÓRE ZDANIE WYGRYWA.

    Historia, bo bez niej ten test wygląda na przesadę: do poprawki Z73p
    gałąź linii ujemnej stała pierwsza, przez co gałąź pozycji pilnej była
    martwa (mutacja M347 przeżyła 856 testów). Po odwróceniu kolejności
    zdanie z nazwą pozycji wygrywa — bo mówi, CO ZROBIĆ, a nie tylko, że
    jest źle.

    Kontrola dwustronna w jednym teście: asercja pozytywna (nazwa, termin,
    kwota, saldo) i asercja negatywna (zdanie o linii NIE pada). Sama
    pozytywna przeszłaby także wtedy, gdyby funkcja skleiła oba zdania.
    """
    prognoza = _prognoza(
        [_dzien(date(2026, 9, 19), "-500.00", [_zdarzenie("ZUS", "-1926.76")])],
        pierwszy_dzien_ujemny=date(2026, 9, 19), brakuje=Decimal("500.00"))
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pilnych == 1, "wejscie mialo dac pozycje pilna"
    powod = co_mnie_czeka.powod_powiadomienia(wynik, prognoza=prognoza,
                                              dzis=date(2026, 9, 18))
    assert powod is not None, "pozycja pilna nie obudzila systemu"
    assert "ZUS" in powod
    assert "2026-09-19" in powod
    assert "1 926,76" in powod.replace("\u00a0", " ")
    assert "Linia ostrożna" not in powod, \
        "wygralo zdanie o linii — kolejnosc galezi wrocila do stanu sprzed Z73p"


def test_POWOD_przy_zejsciu_za_10_dni_BEZ_pozycji_pilnej_niesie_zdanie_o_LINII():
    """Strażnik OSIĄGALNOŚCI gałęzi drugiej — druga połowa kontroli.

    Przedział własny tej gałęzi: zejście pod kreskę dalej niż 3 dni (więc
    żadna pozycja nie jest pilna), ale bliżej niż 14 (więc system ma się
    obudzić). Dziesiąty dzień leży w środku tego przedziału.

    Bez tego testu odwrócenie kolejności z Z73p wymieniłoby tylko martwą
    gałąź na martwą gałąź — i nikt by tego nie zauważył, bo suita byłaby
    zielona tak samo przed, jak i po.
    """
    prognoza = _prognoza(
        [_dzien(date(2026, 9, 28), "-500.00", [_zdarzenie("VAT", "-600.00")])],
        pierwszy_dzien_ujemny=date(2026, 9, 28), brakuje=Decimal("500.00"))
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pilnych == 0, "wejscie NIE mialo dac pozycji pilnej"
    powod = co_mnie_czeka.powod_powiadomienia(wynik, prognoza=prognoza,
                                              dzis=date(2026, 9, 18))
    assert powod is not None, "zejscie pod kreske za 10 dni nie obudzilo systemu"
    assert "Linia ostrożna" in powod
    assert "2026-09-28" in powod
    assert "VAT" not in powod, "zdanie o linii nie ma nazywac pojedynczej pozycji"


def test_RODZAJE_WYPLYWU_pokrywaja_KOMPLET_rodzajow_prognozy():
    """Strażnik świadomego DRUGIEGO NOŚNIKA podziału rodzajów (znalezisko W3
    Leo, §8 v1.17).

    `RODZAJE_WYPLYWU` nie jest wołaniem cudzej reguły — jest jej powtórzeniem:
    `prognoza_plynnosci` wystawia trzy pojedyncze stałe, ale sam PODZIAŁ na
    wpływy i wypływy mieszka wyłącznie tutaj. v1.17 dopuszcza taki drugi
    nośnik wyłącznie z progiem i strażnikiem — to jest ten strażnik.

    Pilnuje własności mocniejszej niż „wszystkie moje są u nich": każdy rodzaj
    znany prognozie musi być przypisany do JEDNEJ z dwóch stron. Nowy rodzaj
    dopisany w `prognoza_plynnosci` i zapomniany tutaj wypadłby z osi PO CICHU
    — pozycja do zapłacenia zniknęłaby z ekranu przy zielonej suicie.

    Próg konsolidacji (plan wykonawczy, „Świadomy dług z progiem"): pierwszy
    nowy rodzaj zdarzenia w `prognoza_plynnosci`. Wtedy podział przenosi się
    do nośnika prognozy, a tutaj zostaje wołanie.

    UPRZEDZENIE DLA TEGO, KTO BĘDZIE KONSOLIDOWAŁ (uwaga Leo, Z73p3):
    `startswith("RODZAJ_")` złapie także przyszłą stałą ZBIOROWĄ — nazwaną
    `RODZAJE_WYPLYWU` albo podobnie — czyli dokładnie to, co powstanie przy
    konsolidacji tego długu. Zbiór stałych przestanie wtedy być zbiorem
    napisów-rodzajów i ten test padnie z komunikatem MYLĄCYM (będzie wyglądał
    na rozjazd podziału, a będzie zderzeniem nazw). Padnie jednak — próg
    zadziała, a nie przemilczy. Świadomie zostawiamy to zdaniem
    w dokumentacji zamiast kodem filtrującym: kod na okoliczność, która ma
    nastąpić raz i od razu zostać usunięta, jest droższy niż ostrzeżenie.
    """
    wszystkie = {v for k, v in vars(pp).items() if k.startswith("RODZAJ_")}
    assert wszystkie, "kontrola licznosci: pomiar nie zobaczyl ANI JEDNEGO rodzaju"
    assert set(co_mnie_czeka.RODZAJE_WYPLYWU) | {pp.RODZAJ_PRZYCHOD_JDG} \
        == wszystkie, (
            "rodzaj znany prognozie nie jest przypisany ani do wyplywow, ani "
            "do wplywow — wypadnie z osi po cichu")
    assert pp.RODZAJ_PRZYCHOD_JDG not in co_mnie_czeka.RODZAJE_WYPLYWU, \
        "kontrola dwustronna: wplyw nie ma prawa byc wyplywem"


def test_stan_nie_wiem_NIE_udaje_zera_pilnych():
    """Zero nigdy nie zastępuje „nie wiem" (D11) — także w liczniku.

    Rozstrzygnięcie Olivera W4, wariant (a). Do poprawki `pilnych` miało
    wartość domyślną `0`, więc gałąź „nie wiem" mówiła „zero pilnych" —
    czyli DOBRĄ WIADOMOŚĆ tam, gdzie nie ma żadnej wiadomości. To pole
    przechodzi granicę HTTP (Z76) i trafia na ekran (Z79), więc kłamstwo
    dojechałoby do człowieka.

    Kontrola dwustronna, bo bez niej `pilnych = None` zawsze też by przeszło:
    „policzyłem i nie ma pilnych" to stan RÓŻNY od „nie liczyłem" i ma zostać
    zerem, nie pustką.
    """
    nie_wiem = pp.Prognoza(stan=pp.STAN_NIE_WIEM, dni=None)
    wynik = co_mnie_czeka.zbuduj(prognoza=nie_wiem, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pilnych is None, "brak wiedzy udaje dobra wiadomosc"

    policzona = _prognoza([
        _dzien(date(2026, 9, 30), "9000.00", [_zdarzenie("ZUS", "-1926.76")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=policzona, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert wynik.pozycje != (), "kontrola licznosci: os miala cos zawierac"
    assert wynik.pilnych == 0
    assert wynik.pilnych is not None, \
        "'policzylem i nie ma' to inny stan niz 'nie liczylem'"


def test_NAJBLIZSZY_wyplyw_jest_najblizszy_takze_przy_ODWROTNEJ_kolejnosci_dni():
    """Nazwa pola jest obietnicą wobec ekranu (znalezisko D9 Leo).

    Silnik oddaje `prognoza.dni` posortowane rosnąco, ale to własność CUDZEJ
    listy, nie nasza gwarancja. `pozycje[0]` przy wejściu w innej kolejności
    pokazywałby wypływ NAJDALSZY pod etykietą „najbliższy" — i wyglądałby
    przy tym na całkowicie poprawny.

    To samo dotyczy powiadomienia: budzi nas pozycja najbliższa, nie pierwsza
    na liście. Oba miejsca sprawdzone jednym wejściem.
    """
    prognoza = _prognoza([
        _dzien(date(2026, 9, 21), "-90.00", [_zdarzenie("PIT", "-40.00")]),
        _dzien(date(2026, 9, 19), "-50.00", [_zdarzenie("ZUS", "-1926.76")]),
    ])
    wynik = co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None,
                                 dzis=date(2026, 9, 18))
    assert len(wynik.pozycje) == 2, "kontrola licznosci: oba dni mialy wejsc"
    assert wynik.najblizszy_wyplyw == date(2026, 9, 19)

    powod = co_mnie_czeka.powod_powiadomienia(wynik, prognoza=prognoza,
                                              dzis=date(2026, 9, 18))
    assert powod is not None
    assert "ZUS" in powod, "powiadomienie nazwalo pozycje dalsza, nie najblizsza"
