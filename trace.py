#!/usr/bin/env python
import io
from pathlib import Path
from sys import settrace, setprofile
import builtins


def run(cmd, trace_func, globals=None, locals=None):
    """
    Debug a statement executed via the exec() function.

    globals defaults to __main__.dict; locals defaults to globals.
    """
    if globals is None:
        import __main__

        globals = __main__.__dict__

    if locals is None:
        locals = globals

    settrace(trace_func)
    try:
        exec(cmd, globals, locals)
    finally:
        setprofile(None)


def runscript(script_file: Path, trace_func):
    # The script has to run in __main__ namespace (or imports from
    # __main__ will break).
    #
    # So we clear up the __main__ and set several special variables
    # (this gets rid of pdb's globals and cleans old variables on restarts).
    import __main__

    __main__.__dict__.clear()
    __main__.__dict__.update(
        {
            "__name__": "__main__",
            "__file__": str(script_file),
            "__builtins__": builtins,
        }
    )

    with io.open_code(str(script_file)) as fp:
        file_body = fp.read()
        statement = compile(file_body, str(script_file), "exec")

    run(statement, trace_func)
