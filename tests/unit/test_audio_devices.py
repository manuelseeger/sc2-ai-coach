import importlib


def test_select_preferred_microphone_index_prefers_nvidia_broadcast(monkeypatch):
    audio_devices = importlib.import_module("runtime.audio_devices")

    class FakeAudio:
        def get_device_count(self):
            return 3

        def get_device_info_by_index(self, index):
            devices = {
                0: {"name": "Microphone Array", "maxInputChannels": 2},
                1: {"name": "NVIDIA Broadcast", "maxInputChannels": 1},
                2: {"name": "Speakers", "maxInputChannels": 0},
            }
            return devices[index]

        def terminate(self):
            return None

    monkeypatch.setattr(audio_devices, "_get_audio", lambda: FakeAudio())

    assert audio_devices.select_preferred_microphone_index() == 1


def test_select_preferred_microphone_index_falls_back_to_default(monkeypatch):
    audio_devices = importlib.import_module("runtime.audio_devices")

    class FakeAudio:
        def get_device_count(self):
            return 2

        def get_device_info_by_index(self, index):
            devices = {
                0: {"name": "Microphone Array", "maxInputChannels": 2},
                1: {"name": "Headset Mic", "maxInputChannels": 1},
            }
            return devices[index]

        def terminate(self):
            return None

    monkeypatch.setattr(audio_devices, "_get_audio", lambda: FakeAudio())

    assert audio_devices.select_preferred_microphone_index() is None


def test_get_microphone_name_uses_default_input_when_index_missing(monkeypatch):
    audio_devices = importlib.import_module("runtime.audio_devices")

    class FakeAudio:
        def get_default_input_device_info(self):
            return {"name": "Default Mic"}

        def terminate(self):
            return None

    monkeypatch.setattr(audio_devices, "_get_audio", lambda: FakeAudio())

    assert audio_devices.get_microphone_name(None) == "Default Mic"
