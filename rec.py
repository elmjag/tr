#!/usr/bin/env python
from sys import argv
from pathlib import Path
from trace import runscript
from utils import Tracer, Records, get_record_file


class Recorder(Tracer):
    def __init__(self, script_file: Path, records, debug_logging=False):
        super().__init__(script_file, records, debug_logging)
        self.record_stack_top = False

    def _record_stack_top(self, frame):
        self.record_stack_top = False
        val = self.peek_stack(frame, 1)
        self.records.write_value(val)

    def _record_result(self, frame, opcode_arg):
        func = self.peek_stack(frame, opcode_arg + 1)
        return self.outside_call(func)

    def __call__(self, frame, event, arg):
        code_obj = frame.f_code

        if code_obj.co_filename != self.script_file:
            return None

        self._print(frame, event, arg)

        if event == "opcode":
            opcode = code_obj.co_code[frame.f_lasti]
            opcode_arg = code_obj.co_code[frame.f_lasti + 1]

            self._print(f"--{opcode=}->", frame.f_lasti, self.opname[opcode], opcode_arg)

            if self.record_stack_top:
                self._record_stack_top(frame)

            if opcode == self.CALL_FUNCTION:
                self.record_stack_top = self._record_result(frame, opcode_arg)

        frame.f_trace_opcodes = True

        return self


script_file = Path(argv[1]).absolute()
record_file = get_record_file(script_file)

with record_file.open("wb") as rec_f:
    runscript(script_file, Recorder(script_file, Records(rec_f), False))
