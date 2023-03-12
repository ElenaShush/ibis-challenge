from typing import overload
from pathlib import Path

END_LINE_CHARS = "\r\n"

@overload
def replace_path2str(obj: list) -> list:
    pass

@overload
def replace_path2str(obj: dict) -> dict:
    pass

def replace_path2str(obj: list | dict) -> list | dict:
    if isinstance(obj, dict):
        new_dt = {}
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                new_dt[key] = replace_path2str(value)
            else:
                if isinstance(value, Path):
                    value = str(value)
                new_dt[key] = value
        return new_dt
    else:
        new_lst = []
        for el in obj:
            if isinstance(el, (dict, list)):
                new_lst.append(replace_path2str(el))
            else:
                if isinstance(el, Path):
                    el = str(el)
                new_lst.append(el)
        return new_lst