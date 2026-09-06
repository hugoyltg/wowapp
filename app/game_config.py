"""AzerothCore Configuration Manager.

Safely reads, updates, and preserves AzerothCore configuration files (.conf):
- playerbots.conf
- worldserver.conf
- individualProgression.conf
- authserver.conf

Features:
- Comment and formatting preservation
- Automatic timestamped backup creation before saving
- Curated settings definitions for Playerbots, World Rates, Individual Progression, and Server
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

from app.config import CONFIG
from app.docker import run_wsl_command


@dataclass
class ConfigOptionDef:
    key: str
    target_file: str  # "playerbots", "world", "progression", "auth"
    category: str  # "playerbots", "world", "progression", "server"
    label: str
    description: str
    val_type: type  # int, float, bool, str
    default: Any
    min_val: Optional[Union[int, float]] = None
    max_val: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    choices: Optional[Dict[Any, str]] = None  # value -> display label
    unit: str = ""


# Curated settings catalogue
CURATED_SETTINGS: List[ConfigOptionDef] = [
    # =========================================================================
    # ⚔ PLAYERBOTS (modules/playerbots.conf)
    # =========================================================================
    ConfigOptionDef(
        key="AiPlayerbot.RandomBotAutologin",
        target_file="playerbots",
        category="playerbots",
        label="Auto-login Random Bots",
        description="Automatically logs in random bots when worldserver boots up.",
        val_type=bool,
        default=True,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.MinRandomBots",
        target_file="playerbots",
        category="playerbots",
        label="Minimum Bot Population",
        description="Minimum number of active random bots populating the world simultaneously.",
        val_type=int,
        default=50,
        min_val=0,
        max_val=500,
        step=5,
        unit="bots",
    ),
    ConfigOptionDef(
        key="AiPlayerbot.MaxRandomBots",
        target_file="playerbots",
        category="playerbots",
        label="Maximum Bot Population",
        description="Maximum number of active random bots allowed online at any time.",
        val_type=int,
        default=50,
        min_val=0,
        max_val=500,
        step=5,
        unit="bots",
    ),
    ConfigOptionDef(
        key="AiPlayerbot.DisableDeathKnightLogin",
        target_file="playerbots",
        category="playerbots",
        label="Disable Death Knight Bots",
        description="When enabled, prevents Death Knight bots from logging in (ideal for Vanilla/TBC progression).",
        val_type=bool,
        default=True,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.RandomBotMinLevel",
        target_file="playerbots",
        category="playerbots",
        label="Bot Minimum Level",
        description="Lowest level a random bot can spawn or reset to.",
        val_type=int,
        default=1,
        min_val=1,
        max_val=80,
        step=1,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.RandomBotMaxLevel",
        target_file="playerbots",
        category="playerbots",
        label="Bot Maximum Level",
        description="Highest level bots can level up to (e.g. 60 for Vanilla, 70 for TBC, 80 for WotLK).",
        val_type=int,
        default=60,
        min_val=1,
        max_val=80,
        step=1,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.RandomBotJoinLfg",
        target_file="playerbots",
        category="playerbots",
        label="Bots Join Dungeon Finder (LFG)",
        description="Allows random bots to queue for dungeons via Looking For Group.",
        val_type=bool,
        default=True,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.RandomBotJoinBG",
        target_file="playerbots",
        category="playerbots",
        label="Bots Join Battlegrounds (PvP)",
        description="Allows random bots to queue for Warsong Gulch, Arathi Basin, and Alterac Valley.",
        val_type=bool,
        default=True,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.RandomBotRpgChance",
        target_file="playerbots",
        category="playerbots",
        label="Bot RPG Behavior Chance",
        description="Probability (0.00 to 1.00) of bots performing roleplay activities in taverns and towns.",
        val_type=float,
        default=0.20,
        min_val=0.0,
        max_val=1.0,
        step=0.05,
    ),
    ConfigOptionDef(
        key="AiPlayerbot.ClassMatchingProfessionChance",
        target_file="playerbots",
        category="playerbots",
        label="Class Matching Profession Chance",
        description="Chance that bots learn professions suited to their class (e.g. Blacksmithing for Warriors).",
        val_type=int,
        default=30,
        min_val=0,
        max_val=100,
        step=5,
        unit="%",
    ),

    # =========================================================================
    # 🌍 WORLD (worldserver.conf)
    # =========================================================================
    ConfigOptionDef(
        key="Rate.XP.Kill",
        target_file="world",
        category="world",
        label="Kill Experience Multiplier",
        description="Experience rate gained from killing monsters and NPCs.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=20.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.XP.Quest",
        target_file="world",
        category="world",
        label="Quest Experience Multiplier",
        description="Experience rate awarded for completing quests.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=20.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.XP.Explore",
        target_file="world",
        category="world",
        label="Exploration XP Multiplier",
        description="Experience rate earned from discovering new zones and map territories.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=10.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.Drop.Money",
        target_file="world",
        category="world",
        label="Gold & Money Drop Multiplier",
        description="Multiplier for gold and copper dropped by creatures.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=20.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.Drop.Item.Uncommon",
        target_file="world",
        category="world",
        label="Green (Uncommon) Drop Rate",
        description="Loot drop rate multiplier for green quality items.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=10.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.Drop.Item.Rare",
        target_file="world",
        category="world",
        label="Blue (Rare) Drop Rate",
        description="Loot drop rate multiplier for blue quality items.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=10.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.Drop.Item.Epic",
        target_file="world",
        category="world",
        label="Purple (Epic) Drop Rate",
        description="Loot drop rate multiplier for purple quality items.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=10.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.Honor",
        target_file="world",
        category="world",
        label="PvP Honor Multiplier",
        description="Multiplier for honor points awarded from PvP honorable kills and battleground objectives.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=10.0,
        step=0.5,
        unit="x",
    ),
    ConfigOptionDef(
        key="Rate.Rest.InGame",
        target_file="world",
        category="world",
        label="In-Game Rest XP Multiplier",
        description="Rate at which characters accumulate rested XP while logged in at an inn or city.",
        val_type=float,
        default=1.0,
        min_val=0.1,
        max_val=10.0,
        step=0.5,
        unit="x",
    ),

    # =========================================================================
    # 🧙 INDIVIDUAL PROGRESSION (modules/individualProgression.conf)
    # =========================================================================
    ConfigOptionDef(
        key="IndividualProgression.StartingProgression",
        target_file="progression",
        category="progression",
        label="Starting Progression Stage",
        description="The story stage that newly created characters start at.",
        val_type=int,
        default=0,
        choices={
            0: "Stage 0: Vanilla Start (Molten Core Prep)",
            1: "Stage 1: Molten Core Cleared",
            2: "Stage 2: Onyxia Cleared (BWL Open)",
            3: "Stage 3: Blackwing Lair Cleared (ZG Open)",
            4: "Stage 4: Pre-AQ War Gates",
            5: "Stage 5: AQ War Effort Open",
            6: "Stage 6: Ahn'Qiraj Cleared (Naxx40 Open)",
            7: "Stage 7: Naxxramas 40 Cleared (Vanilla Cap)",
            8: "Stage 8: TBC Start (Karazhan, Gruul, Magtheridon)",
            9: "Stage 9: TBC Tier 1 (SSC, Tempest Keep)",
            10: "Stage 10: TBC Tier 2 (Hyjal, Black Temple)",
            11: "Stage 11: Zul'Aman Available",
            12: "Stage 12: TBC Tier 4 (Sunwell Plateau)",
            13: "Stage 13: WotLK Start / Death Knights Unlocked",
            14: "Stage 14: WotLK Tier 1 (Ulduar)",
            15: "Stage 15: WotLK Tier 2 (Trial of the Crusader)",
            16: "Stage 16: WotLK Tier 3 (Icecrown Citadel)",
            17: "Stage 17: WotLK Tier 4 (Ruby Sanctum)",
            18: "Stage 18: WotLK Full Completion",
        },
    ),
    ConfigOptionDef(
        key="IndividualProgression.ProgressionLimit",
        target_file="progression",
        category="progression",
        label="Progression Hard Limit",
        description="Maximum stage attainable. 0 = Disabled (play through WotLK), 7 = Vanilla Only, 12 = TBC Only.",
        val_type=int,
        default=0,
        choices={
            0: "0: No Limit (Allow Full Progression up to WotLK 18)",
            7: "7: Lock to Vanilla (Max Level 60, Naxx40 Final)",
            12: "12: Lock to TBC (Max Level 70, Sunwell Final)",
            18: "18: Full WotLK (Max Level 80)",
        },
    ),
    ConfigOptionDef(
        key="IndividualProgression.TbcRacesUnlockProgression",
        target_file="progression",
        category="progression",
        label="TBC Races (Draenei & Blood Elf) Unlock Stage",
        description="Stage required on account to create Draenei and Blood Elves (0 = always available, 8 = after Vanilla).",
        val_type=int,
        default=0,
        choices={
            0: "0: Always Available at start",
            8: "8: Require Vanilla Completed (Stage 8)",
        },
    ),
    ConfigOptionDef(
        key="IndividualProgression.DeathKnightUnlockProgression",
        target_file="progression",
        category="progression",
        label="Death Knight Creation Unlock Stage",
        description="Stage required on account before players can create Death Knights (13 = after TBC).",
        val_type=int,
        default=13,
        choices={
            0: "0: Always Available (Level 55 required in worldserver)",
            8: "8: Unlocked at TBC Start",
            13: "13: Unlocked at WotLK Start (Standard Blizzlike)",
        },
    ),
    ConfigOptionDef(
        key="IndividualProgression.EnforceGroupRules",
        target_file="progression",
        category="progression",
        label="Enforce Progression Group Rules",
        description="Prevents grouping players of different expansion tiers to preserve authentic challenge.",
        val_type=bool,
        default=False,
    ),
    ConfigOptionDef(
        key="IndividualProgression.DisableQuestMarkers",
        target_file="progression",
        category="progression",
        label="Classic Quest Markers Style",
        description="Restores original quest interaction style without modern WotLK map quest objective markers.",
        val_type=bool,
        default=True,
    ),
    ConfigOptionDef(
        key="IndividualProgression.VanillaPowerAdjustment",
        target_file="progression",
        category="progression",
        label="Vanilla Spell Power Scaling",
        description="Scales down WotLK base spell coefficients during Vanilla content for authentic raid difficulty.",
        val_type=bool,
        default=True,
    ),

    # =========================================================================
    # 🛠 SERVER (worldserver.conf / authserver.conf)
    # =========================================================================
    ConfigOptionDef(
        key="PlayerLimit",
        target_file="world",
        category="server",
        label="Max Connected Players",
        description="Maximum simultaneous player connections allowed on the realm.",
        val_type=int,
        default=100,
        min_val=1,
        max_val=2000,
        step=10,
        unit="players",
    ),
    ConfigOptionDef(
        key="WorldServerPort",
        target_file="world",
        category="server",
        label="World Realm Port",
        description="Network port listening for world server client connections (default 8085).",
        val_type=int,
        default=8085,
        min_val=1024,
        max_val=65535,
    ),
    ConfigOptionDef(
        key="LogLevel",
        target_file="world",
        category="server",
        label="Console Log Verbosity",
        description="World server log detail level.",
        val_type=int,
        default=1,
        choices={
            0: "0: Errors Only",
            1: "1: Basic Information (Recommended)",
            2: "2: Detailed / Warnings",
            3: "3: Debug (High verbosity)",
            4: "4: Trace (Full output)",
        },
    ),
]


class AcoreConfigManager:
    """Safely manages reading, parsing, and writing AzerothCore .conf files."""

    def __init__(self, wsl_distro: Optional[str] = None):
        self.wsl_distro = wsl_distro or CONFIG.wsl_distro
        self._unc_base = Path(f"\\\\wsl.localhost\\{self.wsl_distro}\\home\\main\\azerothcore\\azerothcore-wotlk\\env\\dist\\etc")
        self._wsl_base = "/home/main/azerothcore/azerothcore-wotlk/env/dist/etc"

    def get_file_path(self, target: str) -> Tuple[Path, str]:
        """Returns (unc_path, wsl_relative_path) for the target config."""
        file_map = {
            "playerbots": "modules/playerbots.conf",
            "progression": "modules/individualProgression.conf",
            "world": "worldserver.conf",
            "auth": "authserver.conf",
        }
        rel = file_map.get(target, "worldserver.conf")
        unc = self._unc_base / Path(rel)
        wsl = f"{self._wsl_base}/{rel}"
        return unc, wsl

    def read_config_file(self, target: str) -> Tuple[bool, str, List[str]]:
        """Reads configuration lines using direct UNC path or WSL fallback."""
        unc, wsl = self.get_file_path(target)

        # Primary: direct UNC read
        try:
            if unc.exists():
                with open(unc, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                return True, "Loaded successfully via filesystem", lines
        except Exception:
            pass

        # Secondary: read via WSL command fallback
        code, stdout, stderr = run_wsl_command(f"cat {wsl}", wsl_distro=self.wsl_distro)
        if code == 0:
            lines = stdout.splitlines(keepends=True)
            return True, "Loaded successfully via WSL bridge", lines

        return False, f"Could not read config file '{target}': {stderr or 'File not found'}", []

    def parse_values(self, target: str) -> Dict[str, Any]:
        """Extracts parsed key-value pairs from target config."""
        success, _, lines = self.read_config_file(target)
        if not success:
            return {}

        results: Dict[str, Any] = {}
        kv_regex = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s*=\s*(.*?)\s*$")

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            match = kv_regex.match(line)
            if match:
                key, val_str = match.group(1), match.group(2)
                # Strip trailing comment
                if "#" in val_str and not (val_str.startswith('"') and val_str.endswith('"')):
                    val_str = val_str.split("#")[0].strip()
                results[key] = val_str.strip('"').strip("'")

        return results

    def get_all_curated_values(self) -> Dict[str, Any]:
        """Collects current values for all curated options across all config files."""
        parsed_caches: Dict[str, Dict[str, Any]] = {}
        for target in ("playerbots", "world", "progression", "auth"):
            parsed_caches[target] = self.parse_values(target)

        values: Dict[str, Any] = {}
        for opt in CURATED_SETTINGS:
            raw = parsed_caches.get(opt.target_file, {}).get(opt.key)
            if raw is None:
                values[opt.key] = opt.default
            else:
                try:
                    if opt.val_type is bool:
                        values[opt.key] = raw.lower() in ("1", "true", "yes", "on")
                    elif opt.val_type is int:
                        values[opt.key] = int(float(raw))
                    elif opt.val_type is float:
                        values[opt.key] = float(raw)
                    else:
                        values[opt.key] = str(raw)
                except Exception:
                    values[opt.key] = opt.default

        return values

    def save_settings(self, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Updates requested settings across target config files with backup and comment preservation."""
        target_updates: Dict[str, Dict[str, Tuple[ConfigOptionDef, Any]]] = {}
        key_lookup = {opt.key: opt for opt in CURATED_SETTINGS}

        for key, val in updates.items():
            opt = key_lookup.get(key)
            if not opt:
                continue
            target_updates.setdefault(opt.target_file, {})[key] = (opt, val)

        saved_files = []
        errors = []

        for target, kv_items in target_updates.items():
            success, msg = self._save_target_file(target, kv_items)
            if success:
                saved_files.append(target)
            else:
                errors.append(f"{target}: {msg}")

        if errors:
            return False, "; ".join(errors)
        return True, f"Successfully saved configuration for: {', '.join(saved_files)}"

    def _save_target_file(self, target: str, kv_items: Dict[str, Tuple[ConfigOptionDef, Any]]) -> Tuple[bool, str]:
        """Modifies a single config file in place, keeping comments intact and creating a backup."""
        unc, wsl = self.get_file_path(target)
        success, _, lines = self.read_config_file(target)
        if not success:
            return False, f"Cannot read {target} to save"

        # Create timestamped backup
        self._create_backup(target, lines)

        kv_regex = re.compile(r"^(\s*)([A-Za-z0-9_\.]+)(\s*=\s*)(.*?)$")
        modified_keys = set()
        new_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            # If commented line, leave unchanged
            if stripped.startswith("#"):
                new_lines.append(line)
                continue

            match = kv_regex.match(line)
            if match:
                prefix, line_key, eq_part, old_val_part = match.groups()
                if line_key in kv_items:
                    opt, new_val = kv_items[line_key]
                    val_str = self._format_value(opt, new_val)

                    # Preserve trailing comment on that line if any
                    comment_match = re.search(r"(\s+#.*)$", old_val_part)
                    trailing_comment = comment_match.group(1) if comment_match else ""

                    new_line = f"{prefix}{line_key}{eq_part}{val_str}{trailing_comment}\n"
                    new_lines.append(new_line)
                    modified_keys.add(line_key)
                    continue

            new_lines.append(line)

        # Append any new keys that weren't found in file
        for key, (opt, new_val) in kv_items.items():
            if key not in modified_keys:
                val_str = self._format_value(opt, new_val)
                new_lines.append(f"\n# Configured via AzerothCore Manager\n{key} = {val_str}\n")

        # Write out
        return self._write_config_file(unc, wsl, "".join(new_lines))

    def _format_value(self, opt: ConfigOptionDef, val: Any) -> str:
        """Formats Python value into AzerothCore .conf format."""
        if opt.val_type is bool:
            return "1" if bool(val) else "0"
        elif opt.val_type is float:
            return f"{float(val):.2f}".rstrip("0").rstrip(".") if float(val).is_integer() else f"{float(val):.2f}"
        elif opt.val_type is int:
            return str(int(val))
        return str(val)

    def _create_backup(self, target: str, lines: List[str]):
        """Creates a timestamped backup in a .backups directory beside the config."""
        try:
            unc, _ = self.get_file_path(target)
            backup_dir = unc.parent / ".backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"{unc.name}_{ts}.bak"
            with open(backup_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

    def _write_config_file(self, unc: Path, wsl: str, content: str) -> Tuple[bool, str]:
        """Writes content to config file via UNC path or WSL bash fallback."""
        try:
            if unc.parent.exists():
                with open(unc, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                return True, "Saved via filesystem"
        except Exception:
            pass

        # Fallback writing via WSL
        escaped = content.replace("'", "'\\''")
        cmd = f"cat << 'EOF' > '{wsl}'\n{content}\nEOF"
        code, _, stderr = run_wsl_command(cmd, wsl_distro=self.wsl_distro)
        if code == 0:
            return True, "Saved via WSL"
        return False, f"WSL write failed: {stderr}"


# Singleton configuration manager instance
CONFIG_MGR = AcoreConfigManager()
