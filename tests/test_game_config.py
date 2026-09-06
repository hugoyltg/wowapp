"""Tests for AzerothCore Game Configuration Manager."""

from pathlib import Path
import tempfile
import pytest

from app.game_config import AcoreConfigManager, ConfigOptionDef, CURATED_SETTINGS


SAMPLE_CONF = """# Sample AzerothCore Configuration File
# Section A
AiPlayerbot.RandomBotAutologin = 1
AiPlayerbot.MinRandomBots = 50 # Default population
AiPlayerbot.MaxRandomBots = 100
AiPlayerbot.DisableDeathKnightLogin = 0

# World Rates
Rate.XP.Kill = 1.000000
Rate.Drop.Money = 2.5
"""


def test_curated_settings_definitions():
    keys = [opt.key for opt in CURATED_SETTINGS]
    assert "AiPlayerbot.MinRandomBots" in keys
    assert "AiPlayerbot.DisableDeathKnightLogin" in keys
    assert "Rate.XP.Kill" in keys
    assert "IndividualProgression.StartingProgression" in keys


def test_config_parsing_and_formatting(tmp_path):
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    conf_file = modules_dir / "playerbots.conf"
    conf_file.write_text(SAMPLE_CONF, encoding="utf-8")

    mgr = AcoreConfigManager()
    # Override paths to test with temporary folder
    mgr._unc_base = tmp_path
    mgr._wsl_base = str(tmp_path)

    # Test reading
    success, _, lines = mgr.read_config_file("playerbots")
    assert success is True
    assert len(lines) > 5

    # Test parsing
    values = mgr.parse_values("playerbots")
    assert values.get("AiPlayerbot.RandomBotAutologin") == "1"
    assert values.get("AiPlayerbot.MinRandomBots") == "50"
    assert values.get("AiPlayerbot.DisableDeathKnightLogin") == "0"
    assert values.get("Rate.Drop.Money") == "2.5"


def test_config_comment_preserving_save(tmp_path):
    # Setup mock config dir
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    conf_file = modules_dir / "playerbots.conf"
    conf_file.write_text(SAMPLE_CONF, encoding="utf-8")

    mgr = AcoreConfigManager()
    mgr._unc_base = tmp_path
    mgr._wsl_base = str(tmp_path)

    # Modify values: DisableDeathKnightLogin=1, MinRandomBots=75
    updates = {
        "AiPlayerbot.DisableDeathKnightLogin": True,
        "AiPlayerbot.MinRandomBots": 75,
    }

    ok, msg = mgr.save_settings(updates)
    assert ok is True

    # Verify updated file
    content = conf_file.read_text(encoding="utf-8")
    assert "AiPlayerbot.DisableDeathKnightLogin = 1" in content
    assert "AiPlayerbot.MinRandomBots = 75" in content
    # Verify comments are preserved
    assert "# Default population" in content
    assert "# World Rates" in content

    # Verify backup was created
    backup_dir = modules_dir / ".backups"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("*.bak"))
    assert len(backups) >= 1
