"""Was hinaufgereicht wurde, muss unversehrt wieder herauskommen.

Eine halb angekommene Wortliste sieht aus wie eine ganze — bis mitten im
Schuljahr Einheiten fehlen, die niemand vermisst hat. Jeder Test hier baut
genau einen Weg ein, auf dem das passieren könnte, und verlangt, dass
``abholen.py`` ihn findet.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

# `abholen.py` ist ein Werkzeug neben der Werkstatt-Seite, kein Paketmodul -
# geladen wird es deshalb an seinem Pfad.
_PFAD = Path(__file__).resolve().parents[1] / "werkstatt" / "abholen.py"
_SPEZ = importlib.util.spec_from_file_location("abholen", _PFAD)
abholen = importlib.util.module_from_spec(_SPEZ)
_SPEZ.loader.exec_module(abholen)


TEILGROESSE = 64   # klein, damit die Tests mehrere Stücke bekommen


def _ablegen(ordner: Path, roh: bytes, name: str = "wortliste.xlsx",
             **abweichend) -> Path:
    """Einen Upload hinlegen, wie die Seite ihn ablegt."""
    text = base64.b64encode(roh).decode("ascii")
    stücke = [text[i:i + TEILGROESSE] for i in range(0, len(text), TEILGROESSE)]

    kennung = "wl-test"
    uploads = ordner / "uploads"
    (uploads / kennung / "teile").mkdir(parents=True, exist_ok=True)
    for n, stück in enumerate(stücke):
        (uploads / kennung / "teile" / f"{n:04d}.json").write_text(
            json.dumps({"nummer": n, "text": stück}), "utf-8")

    kopf = {
        "id": kennung, "datei": name, "groesse": len(roh),
        "pruefsumme": hashlib.sha256(roh).hexdigest(),
        "teile": len(stücke), "zeichen": len(text), "fertig": True,
    }
    kopf.update(abweichend)
    pfad = uploads / f"{kennung}.json"
    pfad.write_text(json.dumps(kopf), "utf-8")
    return pfad


def test_was_hinaufging_kommt_unversehrt_zurueck(tmp_path):
    roh = bytes(range(256)) * 40          # kein Text, damit Base64 zählt
    pfad = _ablegen(tmp_path, roh)
    name, zurück = abholen.zusammensetzen(pfad)
    assert name == "wortliste.xlsx"
    assert zurück == roh


def test_ein_umschlag_um_das_dokument_stoert_nicht(tmp_path):
    """Je nach Werkzeug steht das Dokument nackt da oder in einem Umschlag."""
    roh = b"PK\x03\x04" + bytes(range(200))
    pfad = _ablegen(tmp_path, roh)
    nackt = json.loads(pfad.read_text("utf-8"))
    pfad.write_text(json.dumps({"id": "wl-test", "data": nackt,
                                "version": 2}), "utf-8")
    _, zurück = abholen.zusammensetzen(pfad)
    assert zurück == roh


def test_ein_fehlendes_stueck_faellt_auf(tmp_path):
    roh = bytes(range(256)) * 40
    pfad = _ablegen(tmp_path, roh)
    stücke = sorted((tmp_path / "uploads" / "wl-test" / "teile").glob("*.json"))
    stücke[1].unlink()
    with pytest.raises(abholen.Unvollstaendig, match="fehlen"):
        abholen.zusammensetzen(pfad)


def test_ein_verfaelschtes_stueck_faellt_auf(tmp_path):
    """Gleiche Länge, anderer Inhalt — das findet nur die Prüfsumme."""
    roh = bytes(range(256)) * 40
    pfad = _ablegen(tmp_path, roh)
    stück = sorted((tmp_path / "uploads" / "wl-test" / "teile").glob("*.json"))[1]
    daten = json.loads(stück.read_text("utf-8"))
    text = daten["text"]
    daten["text"] = ("B" if text[0] != "B" else "C") + text[1:]
    stück.write_text(json.dumps(daten), "utf-8")
    with pytest.raises(abholen.Unvollstaendig, match="Prüfsumme"):
        abholen.zusammensetzen(pfad)


def test_ein_abgebrochener_upload_wird_nicht_eingelesen(tmp_path):
    """Kein „fertig“ heisst: Der Browser kam nie bis zum Kopf."""
    roh = b"x" * 300
    pfad = _ablegen(tmp_path, roh, fertig=False)
    with pytest.raises(abholen.Unvollstaendig, match="fertig"):
        abholen.zusammensetzen(pfad)


def test_die_datei_landet_unter_ihrem_namen(tmp_path):
    roh = bytes(range(256)) * 10
    _ablegen(tmp_path, roh, name="ep2e_level3.xlsx")
    ziel = tmp_path / "data"
    assert abholen.main([str(tmp_path), "-o", str(ziel)]) == 0
    assert (ziel / "ep2e_level3.xlsx").read_bytes() == roh


def test_ein_name_mit_pfad_bleibt_im_zielordner(tmp_path):
    """„../../etc/passwd“ als Dateiname ist kein Ziel, sondern ein Name."""
    roh = b"x" * 120
    _ablegen(tmp_path, roh, name="../../entwischt.xlsx")
    ziel = tmp_path / "data"
    assert abholen.main([str(tmp_path), "-o", str(ziel)]) == 0
    assert (ziel / "entwischt.xlsx").read_bytes() == roh
    assert not (tmp_path.parent / "entwischt.xlsx").exists()


def test_ein_kaputter_upload_schreibt_keine_datei(tmp_path):
    """Mit einer halben Wortliste täte man nichts Sinnvolles."""
    roh = bytes(range(256)) * 40
    _ablegen(tmp_path, roh)
    stücke = sorted((tmp_path / "uploads" / "wl-test" / "teile").glob("*.json"))
    stücke[0].unlink()
    ziel = tmp_path / "data"
    assert abholen.main([str(tmp_path), "-o", str(ziel)]) == 1
    assert not (ziel / "wortliste.xlsx").exists()


def test_umlaute_und_leerzeichen_im_namen_bleiben(tmp_path):
    """Die Datei heisst, wie sie hiess — und der Import findet sie so."""
    roh = b"PK\x03\x04" + bytes(range(100))
    _ablegen(tmp_path, roh, name="Wörter Liste 2026.xlsx")
    ziel = tmp_path / "data"
    assert abholen.main([str(tmp_path), "-o", str(ziel)]) == 0
    assert (ziel / "Wörter Liste 2026.xlsx").read_bytes() == roh


def test_ein_zweiter_upload_ersetzt_die_datei_gleichen_namens(tmp_path):
    """Wer eine korrigierte Wortliste noch einmal schickt, meint: die neue."""
    _ablegen(tmp_path, b"alt" * 50)
    ziel = tmp_path / "data"
    abholen.main([str(tmp_path), "-o", str(ziel)])
    _ablegen(tmp_path, b"neu" * 50)
    abholen.main([str(tmp_path), "-o", str(ziel)])
    assert (ziel / "wortliste.xlsx").read_bytes() == b"neu" * 50
