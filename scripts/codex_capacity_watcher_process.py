"""Cross-platform process lifecycle helpers used by the CLI and GUI."""

from __future__ import annotations

import ctypes
import os
import signal
from ctypes import wintypes


_WINDOWS = os.name == "nt"
_PROCESS_TERMINATE = 0x0001
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_SYNCHRONIZE = 0x00100000
_WAIT_OBJECT_0 = 0
_STOP_WAIT_MS = 5000
_STILL_ACTIVE = 259
_ERROR_INVALID_HANDLE = 6
_ERROR_INVALID_PARAMETER = 87


def _posix_pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, SystemError):
        return False
    return True


def _kernel32() -> ctypes.WinDLL:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _windows_pid_is_running(pid: int) -> bool:
    kernel32 = _kernel32()
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        # Access restrictions mean that the process probably exists. Keep the
        # PID file in that case so the caller does not start a duplicate.
        return error not in {_ERROR_INVALID_HANDLE, _ERROR_INVALID_PARAMETER}
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            error = ctypes.get_last_error()
            return error not in {_ERROR_INVALID_HANDLE, _ERROR_INVALID_PARAMETER}
        return exit_code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def pid_is_running(pid: int) -> bool:
    """Return whether *pid* identifies a live process.

    Windows does not implement ``os.kill(pid, 0)`` as a portable existence
    check. It can raise ``SystemError`` with ``WinError 6`` for a PID that has
    already exited, so use ``OpenProcess`` and ``GetExitCodeProcess`` there.
    """

    if pid <= 0:
        return False
    if _WINDOWS:
        return _windows_pid_is_running(pid)
    return _posix_pid_is_running(pid)


def _windows_stop_pid(pid: int) -> bool | None:
    kernel32 = _kernel32()
    handle = kernel32.OpenProcess(_PROCESS_TERMINATE | _SYNCHRONIZE, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error in {_ERROR_INVALID_HANDLE, _ERROR_INVALID_PARAMETER}:
            return False
        return None
    try:
        if kernel32.TerminateProcess(handle, 0):
            # TerminateProcess is asynchronous. Keep the handle open until the
            # process exits so callers can safely clean up its PID file.
            if kernel32.WaitForSingleObject(handle, _STOP_WAIT_MS) == _WAIT_OBJECT_0:
                return True
            return None
        error = ctypes.get_last_error()
        if error in {_ERROR_INVALID_HANDLE, _ERROR_INVALID_PARAMETER}:
            return False
        return None
    finally:
        kernel32.CloseHandle(handle)


def stop_pid(pid: int) -> bool | None:
    """Request termination of *pid*.

    ``True`` means a termination request was sent, ``False`` means the process
    was already gone, and ``None`` means the process could not be terminated.
    On Windows, a successful request also waits for process termination.
    """

    if pid <= 0:
        return False
    if _WINDOWS:
        return _windows_stop_pid(pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except (OSError, SystemError):
        return None
    return True
