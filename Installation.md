# Installation

Notes on how to setup dependencies.

## Download openwakeword models

One time, in Python repl:

```Python
import openwakeword
openwakeword.utils.download_models()
```

## Flash attention

https://pypi.org/project/flash-attn/

Set MAX_JOBS=4 if less than 100Gb of RAM



## pytorch with CUDA

Needs a CUDA capabale NVidia GPU to run fast whisper. 

conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia