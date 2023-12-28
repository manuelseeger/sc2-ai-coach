from typing import Any
from .ParseReplay import ParseReplay

functions = [ParseReplay]


class FunctionBase:
    '''Base class for all functions.'''

    def __str__(self):
        return f'{self.__class__}: {self.__doc__}'
    
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError