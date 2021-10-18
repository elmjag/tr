from typing import List, Tuple
from dataclasses import dataclass
from pickle import dumps, loads


@dataclass
class CodeObject:
    filename: str  # co_filename
    code: bytes  # co_code
    lines: List[Tuple[int, int, int]]  # co_lines() result


@dataclass
class Frame:
    lineno: int  # f_lineno
    locals: dict  # f_locals
    code: CodeObject  # f_code

    @property
    def source_file(self):
        # shortcut for code.filename
        return self.code.filename


def encode_frame(frame) -> bytes:
    def _get_locals():
        locals = {}

        for name, val in frame.f_locals.items():
            if name.startswith("__"):
                continue

            locals[name] = repr(val)

        return locals

    f_code = frame.f_code
    code = CodeObject(
        filename=f_code.co_filename,
        code=f_code.co_code,
        lines=list(f_code.co_lines()),
    )

    f = Frame(lineno=frame.f_lineno, locals=_get_locals(), code=code)

    return dumps(f)


def decode_frame(data: bytes) -> Frame:
    f = loads(data)
    return f
