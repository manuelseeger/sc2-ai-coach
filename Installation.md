# Installation

The project is managed with uv: https://docs.astral.sh/uv/. 

Add full dependencies
```sh
> uv sync --extra standard
```

Some dependencies need manual setup:

## pytorch with CUDA

Needs CUDA and a capabale NVidia GPU to run fast whisper.

Install with uv: https://docs.astral.sh/uv/guides/integration/pytorch/

## Flash attention

https://pypi.org/project/flash-attn/

Notes: 
- Get C++ build tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  - MSVC C++ 2022 build tools latest
  - Windows 11 SDK
- Set MAX_JOBS=4 if less than 100Gb of RAM

Build with uv but you need to have torch installed first. 

## tesseract

Install tesseract with language data. (Windows: https://github.com/UB-Mannheim/tesseract/wiki).
If installed to non-default location adjust tessdata_dir in config.

## Fast-SSIM 

[external/fast_ssim](external/fast_ssim) requires the Microsoft Visual C++ Redistributable packages for Visual Studio 2013.

https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170

## Realtime-TTS

Install with your preferred engine, for example realtimetts[system,coqui]

Requires C++ redistributable
