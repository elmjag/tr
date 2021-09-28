from pathlib import Path


class Records:
    PROTOCOL = 0
    import pickle

    def __init__(self, records_file):
        self.records_file = records_file

    def write_value(self, value):
        self.pickle.dump(value, self.records_file, protocol=self.PROTOCOL)

    def get_value(self):
        value = self.pickle.load(self.records_file)
        return value


class Tracer:
    # do import at class scope, as the module
    # scope is not available during tracing
    from mytrace import peek_stack, overwrite_stack_value
    from dis import opname
    from types import FunctionType

    #
    # opcode numbers, for quicker lookup
    #
    import dis

    CALL_FUNCTION = dis.opmap["CALL_FUNCTION"]

    def __init__(self, script_file: Path, records, debug_logging=False):
        self.script_file = str(script_file)
        self.records = records

        if debug_logging:
            self._print = self._do_print

    def _do_print(self, *args):
        print(*args)

    def _print(self, *arg):
        # swallow all self._print() calls by default
        pass

    def outside_call(self, func):
        if not isinstance(func, self.FunctionType):
            # probably builtin function or method
            #print("build in, record it")
            return True

        outside_call = func.__code__.co_filename != self.script_file
        #print("snake code record it?", outside_call)

        return outside_call



def get_record_file(script_file: Path) -> Path:
    name = f"{script_file.name}-records"
    return Path(script_file.parent, name)
