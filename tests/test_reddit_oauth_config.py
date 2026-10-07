import sys
import types
from pathlib import Path

# Stub praw/prawcore so we can import the scraper without Reddit deps.
praw = types.ModuleType("praw")
class _Reddit:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.user = types.SimpleNamespace(me=lambda: types.SimpleNamespace(name="tester"))
praw.Reddit = _Reddit
sys.modules["praw"] = praw
sys.modules["prawcore"] = types.ModuleType("prawcore")
sys.modules["prawcore"].exceptions = types.SimpleNamespace(
    Redirect=Exception, Forbidden=Exception, PrawcoreException=Exception
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RedditDB"))
import scrape_malefashion as sm


def test_password_only_config_fails_fast(monkeypatch, tmp_path):
    cfg = tmp_path / "config.ini"
    cfg.write_text(
        "[DEFAULT]\n"
        "client_id = abc\n"
        "client_secret = def\n"
        "username = u\n"
        "password = p\n"
        "user_agent = FashionDB/1.0 by tester\n"
    )
    monkeypatch.setattr(sm.ScraperConfig, "CONFIG_PATH", cfg)
    reddit, budget = sm.create_reddit_client()
    assert reddit is None and budget is None


def test_refresh_token_builds_client(monkeypatch, tmp_path):
    cfg = tmp_path / "config.ini"
    cfg.write_text(
        "[DEFAULT]\n"
        "client_id = abc\n"
        "client_secret = def\n"
        "refresh_token = refresh123\n"
        "user_agent = FashionDB/1.0 by tester\n"
    )
    monkeypatch.setattr(sm.ScraperConfig, "CONFIG_PATH", cfg)
    reddit, budget = sm.create_reddit_client()
    assert reddit is not None
    assert reddit.kwargs.get("refresh_token") == "refresh123"
    assert "password" not in reddit.kwargs
    assert budget is not None


def test_example_ini_has_refresh_token_not_password():
    example = Path(__file__).resolve().parents[1] / "config" / "config.ini.example"
    text = example.read_text()
    assert "refresh_token" in text
    assert "password = YOUR_REDDIT_PASSWORD" not in text
