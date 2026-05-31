# Installation

The project is managed with uv: https://docs.astral.sh/uv/. 

Add full dependencies
```sh
> uv sync --extra standard
```

Some dependencies need manual setup:

## tesseract

Install tesseract with language data. (Windows: https://github.com/UB-Mannheim/tesseract/wiki).
If installed to non-default location adjust tessdata_dir in config.

## Fast-SSIM 

[external/fast_ssim](external/fast_ssim) requires the Microsoft Visual C++ Redistributable packages for Visual Studio 2013.

https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170

## Realtime-TTS

Install with your preferred engine, for example realtimetts[system,coqui]

Requires C++ redistributable


## Custom Wakeword

To train a custom wakeword: 

```
uv tool install livekit-wakeword[train,eval,export]
livekit-wakeword setup --config configs/prod.yaml
```
See https://github.com/livekit/livekit-wakeword

Prerequisites: 
https://github.com/espeak-ng/espeak-ng/

