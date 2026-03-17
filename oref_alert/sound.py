"""Sound playback for alert notifications."""

from __future__ import annotations

import os
import platform
import winsound

from oref_alert.config import AppConfig


def play_alert_sound(config: AppConfig) -> None:
    """Play a notification sound according to the user configuration."""
    if config.sound_mode == "silent":
        return

    if config.sound_mode == "custom" and config.custom_sound_path:
        path = os.path.abspath(config.custom_sound_path)
        if os.path.isfile(path):
            try:
                # SND_ASYNC so it doesn't block the UI thread.
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception:
                pass

    # Default sound: use system exclamation/beep
    try:
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        # Fallback to simple beep
        try:
            winsound.Beep(1000, 200)
        except Exception:
            pass
