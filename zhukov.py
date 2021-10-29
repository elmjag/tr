from typing import List, Tuple
from dataclasses import dataclass
from pickle import dumps, loads


@dataclass
class CodeObject:
    filename: str  # co_filename
    varnames: tuple  # co_varnames
    names: tuple  # co_names
    consts: list  # co_consts
    code: bytes  # co_code
    lines: List[Tuple[int, int, int]]  # co_lines() result


@dataclass
class Frame:
    lineno: int  # f_lineno
    lasti: int  # f_lasti
    globals: dict  # f_globals
    locals: dict  # f_locals
    code: CodeObject  # f_code

    @property
    def source_file(self):
        # shortcut for code.filename
        return self.code.filename


def encode_frame(frame) -> bytes:
    def _get_vars(vars):
        locals = {}

        for name, val in vars.items():
            locals[name] = repr(val)

        return locals

    f_code = frame.f_code

    code = CodeObject(
        filename=f_code.co_filename,
        varnames=f_code.co_varnames,
        names=f_code.co_names,
        consts=[repr(n) for n in f_code.co_consts],
        code=f_code.co_code,
        lines=list(f_code.co_lines()),
    )

    f = Frame(
        lineno=frame.f_lineno,
        lasti=frame.f_lasti,
        globals=_get_vars(frame.f_globals),
        locals=_get_vars(frame.f_locals),
        code=code,
    )

    return dumps(f)


def decode_frame(data: bytes) -> Frame:
    f = loads(data)
    return f
