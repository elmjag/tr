from pathlib import Path


class Records:
    PROTOCOL = 0
    import pickle
    import _thread
    from enum import Enum

    class ValueType(Enum):
        NORMAL = 0
        THREAD_LOCK = 1

    def __init__(self, records_file):
        self.records_file = records_file

    def _write(self, value):
        self.pickle.dump(value, self.records_file, protocol=self.PROTOCOL)

    def write_value(self, value):
        if isinstance(value, self._thread.LockType):
            self._write(self.ValueType.THREAD_LOCK.value)
            return

        self._write(self.ValueType.NORMAL.value)
        self._write(value)

    def get_value(self):
        value = self.pickle.load(self.records_file)
        return value


class Tracer:
    # do import at class scope, as the module
    # scope is not available during tracing
    from sys import stderr
    from mytrace import peek_stack, overwrite_stack_value
    from dis import opname
    from types import (
        FunctionType,
        BuiltinFunctionType,
        BuiltinMethodType,
        MethodDescriptorType,
    )

    #
    # opcode numbers, for quicker lookup
    #
    import dis

    CALL_FUNCTION = dis.opmap["CALL_FUNCTION"]
    CALL_METHOD = dis.opmap["CALL_METHOD"]

    def __init__(self, script_file: Path, records: Records, debug_logging=False):
        self.script_file = str(script_file)
        self.records = records

        if debug_logging:
            self._print = self._do_print

    def _do_print(self, *args):
        print(*args, file=self.stderr)

    def _print(self, *arg):
        # swallow all self._print() calls by default
        pass

    def outside_call(self, func):
        if not isinstance(func, self.FunctionType):
            # probably builtin function or method
            return True

        outside_call = func.__code__.co_filename != self.script_file

        return outside_call


def get_record_file(script_file: Path) -> Path:
    name = f"{script_file.name}-records"
    return Path(script_file.parent, name)
