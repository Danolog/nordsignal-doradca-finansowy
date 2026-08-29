"""Strazniki wskazania bazy zmienna srodowiskowa `AI_CFO_BAZA` (Z52).

Powod istnienia zadania: mandat „agenty pracuja bez udzialu Darka" stoi na
warunku „agenty pracuja na KOPII bazy, nigdy na `cfo_database.db`". Do Z52 ten
warunek byl obietnica — nie bylo mechanizmu, ktory dalby sie zlamac.

Tryb awarii, przed ktorym broni to zadanie, brzmi: „patrzylem w niewlasciwa
baze i wygladalo dobrze". Dlatego samo wskazanie nie wystarcza — rozwiazana
sciezka musi byc WIDOCZNA, a pod pytestem produkcyjna musi byc BLEDEM.
"""

import os
from pathlib import Path

import pytest

from silnik.rdzen import magazyn


# --- rozwiazywanie sciezki ------------------------------------------------

def test_zmienna_srodowiskowa_WSKAZUJE_baze(tmp_path, monkeypatch):
    cel = tmp_path / "kopia.db"
    monkeypatch.setenv("AI_CFO_BAZA", str(cel))
    assert magazyn.sciezka_bazy() == cel


def test_brak_zmiennej_zachowuje_dotychczasowe_zachowanie(monkeypatch):
    """Kontrola dwustronna: bez zmiennej nic sie nie zmienia.

    Przez `_rozwiaz_sciezke`, nie `sciezka_bazy` — patrz docstring tej funkcji.
    Ten test NIE otwiera bazy, wiec wynik „sciezka produkcyjna" jest tu
    obserwacja, nie proba dostepu.
    """
    monkeypatch.delenv("AI_CFO_BAZA", raising=False)
    assert magazyn._rozwiaz_sciezke() == magazyn.SCIEZKA_DOMYSLNA


def test_zmienna_PUSTA_znaczy_brak_zmiennej(monkeypatch):
    """`AI_CFO_BAZA=""` rozwiazaloby sie na katalog biezacy — czyli na baze,
    ktorej nazwy nikt nie podal. Pusty napis znaczy „nie wskazano"."""
    monkeypatch.setenv("AI_CFO_BAZA", "   ")
    assert magazyn._rozwiaz_sciezke() == magazyn.SCIEZKA_DOMYSLNA


def test_polacz_BEZ_argumentu_idzie_za_zmienna(tmp_path, monkeypatch):
    """To jest sedno zadania: `app.py:86` wola `polacz()` bez argumentu."""
    cel = tmp_path / "wskazana.db"
    monkeypatch.setenv("AI_CFO_BAZA", str(cel))
    polaczenie = magazyn.zmigruj_i_polacz()
    polaczenie.close()
    assert cel.exists(), "polacz() otworzyl inna baze niz wskazana"


def test_argument_WYGRYWA_ze_zmienna(tmp_path, monkeypatch):
    """Parametr `sciezka` zostaje — uzywaja go wszystkie 500+ testow."""
    monkeypatch.setenv("AI_CFO_BAZA", str(tmp_path / "ze-zmiennej.db"))
    jawna = tmp_path / "z-argumentu.db"
    magazyn.zmigruj_i_polacz(jawna).close()
    assert jawna.exists()
    assert not (tmp_path / "ze-zmiennej.db").exists()


# --- straznik: pod pytestem NIGDY baza produkcyjna ------------------------

def test_pod_pytestem_produkcyjna_sciezka_jest_BLEDEM(monkeypatch):
    monkeypatch.delenv("AI_CFO_BAZA", raising=False)
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.sciezka_bazy()
    assert "cfo_database.db" in str(blad.value)
    assert "AI_CFO_BAZA" in str(blad.value), \
        "komunikat ma mowic, co zrobic, nie tylko ze zle"


def test_straznik_ISTNIEJE_a_nie_tylko_powinien():
    """Kontrola licznosci. Test wyzej przeszedlby takze wtedy, gdyby bledem
    rzucalo cokolwiek innego — a lista straznikow byla pusta."""
    assert magazyn.STRAZNICY_SCIEZKI, \
        "conftest.py nie zainstalowal straznika sciezki produkcyjnej"


def test_straznik_PRZEPUSZCZA_sciezke_spoza_produkcji(tmp_path, monkeypatch):
    """Kontrola dwustronna: bramka, ktora blokuje wszystko, nie jest bramka."""
    monkeypatch.setenv("AI_CFO_BAZA", str(tmp_path / "wolno.db"))
    assert magazyn.sciezka_bazy() == tmp_path / "wolno.db"


# --- widocznosc: „patrzylem w niewlasciwa baze i wygladalo dobrze" --------

def test_opis_bazy_mowi_ktora_baze_otwarto(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_CFO_BAZA", str(tmp_path / "kopia-robocza.db"))
    opis = magazyn.opis_bazy()
    assert opis.sciezka == tmp_path / "kopia-robocza.db"
    assert opis.domyslna is False


def test_opis_bazy_przy_domyslnej_mowi_ze_domyslna():
    """Kontrola dwustronna do testu wyzej. Sciezka podana jawnie, bo
    `opis_bazy()` bez argumentu przeszlaby przez bramke — i slusznie."""
    opis = magazyn.opis_bazy(magazyn.SCIEZKA_DOMYSLNA)
    assert opis.domyslna is True
    assert opis.sciezka == magazyn.SCIEZKA_DOMYSLNA
