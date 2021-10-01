from dataclasses import dataclass
from pickle import dumps, loads


@dataclass
class Frame:
    lineno: int  # f_lineno
    locals: dict  # f_locals


def encode_frame(frame) -> bytes:
    def _get_locals():
        locals = {}

        for name, val in frame.f_locals.items():
            if name.startswith("__"):
                continue

            locals[name] = repr(val)

        return locals

    f = Frame(lineno=frame.f_lineno, locals=_get_locals())
    return dumps(f, protocol=0)


def decode_frame(data: bytes) -> Frame:
    f = loads(data)
    return f
