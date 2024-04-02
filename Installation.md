# Installation

Notes on how to setup dependencies; In general, create a new env with conda: 

```sh
conda env create --name aicoach311 --file=environments-cp311.yml
```
Python 3.11 is the only version that works with all dependencies at this point. 

Some dependencies need manual setup:

## Download openwakeword models

One time, in Python repl:

```python
import openwakeword
openwakeword.utils.download_models()
```

## Flash attention

https://pypi.org/project/flash-attn/

Set MAX_JOBS=4 if less than 100Gb of RAM

## pytorch with CUDA

Needs a CUDA capabale NVidia GPU to run fast whisper. 

conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia

## tesseract

Install tesseract with language data. (Windows: https://github.com/UB-Mannheim/tesseract/wiki).
If installed to non-default location adjust tessdata_dir in config.

## RealtimeTTS

https://github.com/KoljaB/RealtimeTTS?tab=readme-ov-file

Install manually then reinstall openai as RealtimeTTS downgrades openai on installation.