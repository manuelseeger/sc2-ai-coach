# -*- coding: utf-8 -*-
# Simplified wrapper for Fast-SSIM: https://github.com/chinue/Fast-SSIM
import ctypes
import os

import numpy as np
from numpy.typing import NDArray

ssim_dll_path = os.path.split(os.path.realpath(__file__))[0]
ssim_dll_name = "ssim"

dll = np.ctypeslib.load_library(ssim_dll_name, ssim_dll_path)

type_dict = {
    "int": ctypes.c_int,
    "float": ctypes.c_float,
    "double": ctypes.c_double,
    "void": None,
    "int32": ctypes.c_int32,
    "uint32": ctypes.c_uint32,
    "int16": ctypes.c_int16,
    "uint16": ctypes.c_uint16,
    "int8": ctypes.c_int8,
    "uint8": ctypes.c_uint8,
    "byte": ctypes.c_uint8,
    "char*": ctypes.c_char_p,
    "float*": np.ctypeslib.ndpointer(dtype="float32", ndim=1, flags="CONTIGUOUS"),
    "int*": np.ctypeslib.ndpointer(dtype="int32", ndim=1, flags="CONTIGUOUS"),
    "byte*": np.ctypeslib.ndpointer(dtype="uint8", ndim=1, flags="CONTIGUOUS"),
}


def get_dll_function(
    res_type="float",
    func_name="PSNR_Byte",
    arg_types=["Byte*", "int", "int", "int", "Byte*"],
):
    func = dll.__getattr__(func_name)
    func.restype = type_dict[res_type]
    func.argtypes = [type_dict[str.lower(x).replace(" ", "")] for x in arg_types]
    return func


class DLL:

    # float PSNR_Byte(Byte* pDataX, Byte* pDataY, int step, int width, int height, int maxVal);
    PSNR_Byte = get_dll_function(
        "float", "PSNR_Byte", ["Byte*", "Byte*", "int", "int", "int", "int"]
    )

    # float PSNR_Float(float* pDataX, float* pDataY, int step, int width, int height, double maxVal);
    PSNR_Float = get_dll_function(
        "float", "PSNR_Float", ["float*", "float*", "int", "int", "int", "double"]
    )

    # float SSIM_Byte(Byte* pDataX, Byte* pDataY, int step, int width, int height, int win_size, int maxVal);
    SSIM_Byte = get_dll_function(
        "float", "SSIM_Byte", ["Byte*", "Byte*", "int", "int", "int", "int", "int"]
    )

    # float SSIM_Float(float* pDataX, float* pDataY, int step, int width, int height, int win_size, double maxVal);
    SSIM_Float = get_dll_function(
        "float",
        "SSIM_Float",
        ["float*", "float*", "int", "int", "int", "int", "double"],
    )


def psnr(x: NDArray[np.uint8], y: NDArray[np.uint8], max_value: int = None) -> float:
    [h, w, c] = x.shape
    x = x.astype("float32") if (x.dtype == "float64") else x
    y = y.astype("float32") if (y.dtype == "float64") else y
    if x.dtype == "uint8" and y.dtype == "uint8":
        return DLL.PSNR_Byte(
            x.reshape([-1]),
            y.reshape([-1]),
            w * c,
            w,
            h,
            255 if (max_value == None) else int(max_value),
        )
    if x.dtype == "float32" and y.dtype == "float32":
        return DLL.PSNR_Float(
            x.reshape([-1]),
            y.reshape([-1]),
            w * c,
            w,
            h,
            255.0 if (max_value == None) else float(max_value),
        )


def ssim(
    x: NDArray[np.uint8], y: NDArray[np.uint8], max_value: int = None, win_size: int = 7
) -> float:
    [h, w, c] = x.shape
    x = x.astype("float32") if (x.dtype == "float64") else x
    y = y.astype("float32") if (y.dtype == "float64") else y
    if x.dtype == "uint8" and y.dtype == "uint8":
        return DLL.SSIM_Byte(
            x.reshape([-1]),
            y.reshape([-1]),
            w * c,
            w,
            h,
            win_size,
            255 if (max_value == None) else int(max_value),
        )
    if x.dtype == "float32" and y.dtype == "float32":
        return DLL.SSIM_Float(
            x.reshape([-1]),
            y.reshape([-1]),
            w * c,
            w,
            h,
            win_size,
            255.0 if (max_value == None) else float(max_value),
        )
