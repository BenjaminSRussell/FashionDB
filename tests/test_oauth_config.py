from pathlib import Path
import configparser
def test_example_ini_has_refresh_not_password():
    text = Path("config/config.ini.example").read_text()
    assert "refresh_token" in text
    cfg = configparser.ConfigParser(); cfg.read_string(text)
    assert "refresh_token" in cfg["DEFAULT"]
    assert not (cfg["DEFAULT"].get("password") or "").strip()
