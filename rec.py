#!/usr/bin/env python3
from sys import argv
from pathlib import Path
from trace import runscript
from utils import Tracer, Records, get_record_file


class Recorder(Tracer):
    class ResultIntercept:
        def __init__(self, recoder, records: Records, func):
            self.recorder = recoder
            self.records = records
            self.func = func

        def __call__(self, *args):
            res = self.func(*args)
            self.records.write_value(res)
            self.recorder.tracing_on = True
            return res

    def __init__(self, script_file: Path, records: Records, debug_logging=False):
        super().__init__(script_file, records, debug_logging)
        self.tracing_on = True
        self.last_shown_frame = None

    def _record_result(self, frame, opcode_arg):
        func = self.peek_stack(frame, opcode_arg + 1)
        return self.outside_call(func)

    def _show_frame(self, frame):
        if self.last_shown_frame is frame:
            # already shown
            return

        self.last_shown_frame = frame
        self.dis.dis(frame.f_code, file=self.stderr)

    def __call__(self, frame, event, arg):
        if not self.tracing_on:
            frame.f_trace_opcodes = True
            return None

        code_obj = frame.f_code

        self._print(f"{frame=} {event=} {arg=}")
        if event == "call":
            self._show_frame(frame)

        if event == "opcode":
            opcode = code_obj.co_code[frame.f_lasti]
            opcode_arg = code_obj.co_code[frame.f_lasti + 1]

            self._print(frame.f_lasti, self.opname[opcode], opcode_arg)

            if opcode == self.CALL_METHOD:
                pos = opcode_arg + 2
                f = self.peek_stack(frame, pos)
                if f is None:
                    pos = opcode_arg + 1
                    f = self.peek_stack(frame, pos)

                self._print(f"call method {opcode_arg=} {f=} {type(f)=}")

                if isinstance(f, self.MethodDescriptorType) or isinstance(
                    f, self.BuiltinMethodType
                ):
                    self._print("BUILT IN!")
                    self.overwrite_stack_value(
                        frame, pos, self.ResultIntercept(self, self.records, f)
                    )
                    self.tracing_on = False

        frame.f_trace_opcodes = True

        return self


script_file = Path(argv[1]).absolute()
record_file = get_record_file(script_file)

with record_file.open("wb") as rec_f:
    runscript(script_file, Recorder(script_file, Records(rec_f), False))
