"""Sound playback for alert notifications."""

from __future__ import annotations

import os
import winsound

try:
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except Exception:  # pragma: no cover - depends on local Qt multimedia installation
    QUrl = None  # type: ignore[assignment]
    QAudioOutput = None  # type: ignore[assignment]
    QMediaPlayer = None  # type: ignore[assignment]

from oref_alert.config import AppConfig


_media_player: QMediaPlayer | None = None
_audio_output: QAudioOutput | None = None


def _play_via_qt(path: str) -> bool:
    """Play media via Qt Multimedia (supports mp3 and more)."""
    global _media_player, _audio_output

    if QMediaPlayer is None or QAudioOutput is None or QUrl is None:
        return False

    try:
        if _media_player is None:
            _media_player = QMediaPlayer()
            _audio_output = QAudioOutput()
            _media_player.setAudioOutput(_audio_output)

        assert _audio_output is not None
        _audio_output.setVolume(1.0)
        _media_player.setSource(QUrl.fromLocalFile(path))
        _media_player.play()
        return True
    except Exception:
        return False


def play_alert_sound(config: AppConfig) -> None:
    """Play a notification sound according to the user configuration."""
    if config.sound_mode == "silent":
        return

    if config.sound_mode == "custom" and config.custom_sound_path:
        path = os.path.abspath(config.custom_sound_path)
        if os.path.isfile(path):
            # Prefer Qt media playback to support formats like mp3.
            if _play_via_qt(path):
                return
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
