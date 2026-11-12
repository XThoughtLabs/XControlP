# -*- coding: utf-8 -*-
"""Создаёт (или чинит) ярлык «XControlP» на рабочем столе Windows.

Ярлык запускает «XControlP.pyw» тем же Python, которым запущен этот файл, и показывает значок icon.ico.
Ярлык делает сама Windows (IShellLinkW), поэтому русские буквы в путях не мешают.
Достаточно дважды щёлкнуть этот файл один раз. Если что-то пойдёт не так, появится окно с ошибкой
и рядом файл shortcut-error.txt.
"""
import ctypes
import pathlib
import sys
import traceback
import uuid

HERE = pathlib.Path(__file__).resolve().parent
LAUNCHER = HERE / "XControlP.pyw"
ICON = HERE / "icon.ico"
NAME = "XControlP"
ERROR_FILE = HERE / "shortcut-error.txt"


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, text):
        super().__init__()
        ctypes.memmove(ctypes.byref(self), uuid.UUID(text).bytes_le, 16)


CLSID_SHELL_LINK = GUID("00021401-0000-0000-C000-000000000046")
IID_ISHELL_LINK_W = GUID("000214F9-0000-0000-C000-000000000046")
IID_IPERSIST_FILE = GUID("0000010B-0000-0000-C000-000000000046")
CLSCTX_INPROC_SERVER = 1
CSIDL_DESKTOPDIRECTORY = 0x10

# Method numbers in the COM tables (shobjidl.h / objidl.h).
QUERY_INTERFACE, RELEASE = 0, 2
SET_DESCRIPTION, SET_WORKING_DIRECTORY, SET_ARGUMENTS, SET_SHOW_CMD, SET_ICON_LOCATION, SET_PATH = 7, 9, 11, 15, 17, 20
PERSIST_SAVE = 6


def call(obj, index, argtypes, *args):
    table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    method = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)(table[index])
    return method(obj, *args)


def release(obj):
    table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[RELEASE])(obj)


def desktop():
    buffer = ctypes.create_unicode_buffer(32768)
    ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buffer)
    return pathlib.Path(buffer.value) if buffer.value else HERE.parent


def python_without_console():
    exe = pathlib.Path(sys.executable)
    if exe.name.lower() == "python.exe" and (exe.parent / "pythonw.exe").is_file():
        exe = exe.parent / "pythonw.exe"
    return exe


def make_shortcut():
    ole32 = ctypes.OleDLL("ole32")
    ole32.CoInitialize(None)
    link, persist = ctypes.c_void_p(), ctypes.c_void_p()
    ole32.CoCreateInstance(ctypes.byref(CLSID_SHELL_LINK), None, CLSCTX_INPROC_SERVER,
                           ctypes.byref(IID_ISHELL_LINK_W), ctypes.byref(link))
    try:
        text = (ctypes.c_wchar_p,)
        call(link, SET_PATH, text, str(python_without_console()))
        call(link, SET_ARGUMENTS, text, f'"{LAUNCHER}"')
        call(link, SET_WORKING_DIRECTORY, text, str(HERE))
        call(link, SET_DESCRIPTION, text, "XControlP")
        call(link, SET_ICON_LOCATION, (ctypes.c_wchar_p, ctypes.c_int), str(ICON), 0)
        call(link, SET_SHOW_CMD, (ctypes.c_int,), 1)
        call(link, QUERY_INTERFACE, (ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)),
             ctypes.byref(IID_IPERSIST_FILE), ctypes.byref(persist))
        target = desktop() / f"{NAME}.lnk"
        call(persist, PERSIST_SAVE, (ctypes.c_wchar_p, ctypes.c_int), str(target), 1)
        return target
    finally:
        if persist:
            release(persist)
        release(link)
        ole32.CoUninitialize()


def main():
    try:
        if not LAUNCHER.is_file():
            raise FileNotFoundError(f"Не найден файл {LAUNCHER}")
        make_shortcut()
    except Exception:
        report = traceback.format_exc()
        try:
            ERROR_FILE.write_text(report, encoding="utf-8")
        except OSError:
            pass
        ctypes.windll.user32.MessageBoxW(None, "Ярлык не получилось создать.\n\n" + report, "XControlP", 0x10)


if __name__ == "__main__":
    main()
