from __future__ import annotations

import logging

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

PREFERRED_MICROPHONE_NAME = "nvidia broadcast"


def _get_audio():
    import pyaudio

    return pyaudio.PyAudio()


def _iter_input_devices(audio):
    for index in range(audio.get_device_count()):
        device = audio.get_device_info_by_index(index)
        if device.get("maxInputChannels"):
            yield index, device


def get_microphone_name(device_index: int | None) -> str | None:
    audio = _get_audio()

    try:
        if device_index is None:
            device = audio.get_default_input_device_info()
        else:
            device = audio.get_device_info_by_index(device_index)
    except OSError:
        return None
    finally:
        audio.terminate()

    name = device.get("name")
    return str(name) if name is not None else None


def select_preferred_microphone_index() -> int | None:
    audio = _get_audio()

    try:
        for index, device in _iter_input_devices(audio):
            name = str(device.get("name", ""))
            if PREFERRED_MICROPHONE_NAME in name.lower():
                return index
    except OSError:
        log.warning(
            "Unable to enumerate audio input devices; using system default input"
        )
        return None
    finally:
        audio.terminate()

    log.info("No NVIDIA Broadcast microphone found; using system default input")
    return None
