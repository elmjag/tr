#!/usr/bin/env python
from sys import argv
from pathlib import Path
from trace import runscript
from utils import Tracer, Records, get_record_file


class Replay(Tracer):
    class FuncPatch:
        def __init__(self, return_value):
            self.return_value = return_value

        def __call__(self, *args):
            print(f"patched {args=} {self.return_value=}")
            return self.return_value

    def __init__(self, script_file: Path, records, debug_logging=False):
        super().__init__(script_file, records, debug_logging)

    def _patch_call_function(self, frame):
        code_obj = frame.f_code
        co_code = code_obj.co_code
        #nexti = frame.f_lasti

        opcode = co_code[frame.f_lasti]
        if opcode != self.CALL_FUNCTION:
            return

        opcode_arg = code_obj.co_code[frame.f_lasti + 1]
        func = self.peek_stack(frame, opcode_arg + 1)
        outsider = self.outside_call(func)
        print(f"patchee {func=} {outsider=}")

        if outsider:
            self.overwrite_stack_value(
                frame, opcode_arg + 1, self.FuncPatch(self.records.get_value())
            )

    def __call__(self, frame, event, arg):
        code_obj = frame.f_code

        if code_obj.co_filename != self.script_file:
            return None

        self._print(frame, event, arg)

        if event == "opcode":
            opcode = code_obj.co_code[frame.f_lasti]
            opcode_arg = code_obj.co_code[frame.f_lasti + 1]

            self._print(frame.f_lasti, self.opname[opcode], opcode_arg)
            self._patch_call_function(frame)

        frame.f_trace_opcodes = True
        return self


script_file = Path(argv[1]).absolute()
record_file = get_record_file(script_file)

with record_file.open("rb") as rec_f:
    runscript(script_file, Replay(script_file, Records(rec_f), False))
