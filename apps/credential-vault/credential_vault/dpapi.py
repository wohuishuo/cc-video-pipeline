"""Windows CurrentUser DPAPI adapter with a non-interactive public contract."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DpapiError(RuntimeError):
    """Raised when Windows cannot protect or unprotect a credential."""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _input_blob(value: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(value, len(value))
    blob = _DataBlob(
        len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    )
    return blob, buffer


class DpapiCurrentUserCipher:
    """Protect bytes for the current Windows user; never uses machine scope."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise DpapiError("CurrentUser DPAPI is available only on Windows")
        self._crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    def protect(self, plaintext: bytes, context: bytes) -> bytes:
        return self._transform("CryptProtectData", plaintext, context, clear_output=False)

    def unprotect(self, ciphertext: bytes, context: bytes) -> bytes:
        return self._transform("CryptUnprotectData", ciphertext, context, clear_output=True)

    def _transform(
        self, function_name: str, value: bytes, context: bytes, *, clear_output: bool
    ) -> bytes:
        if not value or not context:
            raise DpapiError("DPAPI input and context must not be empty")
        input_blob, input_buffer = _input_blob(value)
        entropy_blob, entropy_buffer = _input_blob(context)
        output_blob = _DataBlob()
        function = getattr(self._crypt32, function_name)
        succeeded = function(
            ctypes.byref(input_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output_blob),
        )
        # Keep the backing buffers alive through the native call.
        _ = input_buffer, entropy_buffer
        if not succeeded:
            error = ctypes.get_last_error()
            raise DpapiError(f"{function_name} failed with Windows error {error}")
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            if clear_output and output_blob.pbData and output_blob.cbData:
                ctypes.memset(output_blob.pbData, 0, output_blob.cbData)
            if output_blob.pbData:
                self._kernel32.LocalFree(output_blob.pbData)
