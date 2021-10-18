#!/usr/bin/env python
from os import fork
from sys import exit
from pathlib import Path
from socket import socketpair, SOCK_DGRAM
from trace import runscript
from utils import Tracer, Records, get_record_file
from zhukov import encode_frame


class Replay(Tracer):
    class FuncPatch:
        def __init__(self, return_value):
            self.return_value = return_value

        def __call__(self, *args):
            return self.return_value

    def __init__(
        self, script_file: Path, records: Records, ctrl_socket, debug_logging=False
    ):
        super().__init__(script_file, records, debug_logging)
        self._step_mode = "line"
        self._ctrl_socket = ctrl_socket

    def _push_frame_state(self, frame):
        self._ctrl_socket.send(encode_frame(frame))
        self._step_mode = self._ctrl_socket.recv(1024).decode()

    def __call__(self, frame, event, arg):
        code_obj = frame.f_code

        self._print("------>", frame, event, arg)

        if event == self._step_mode:
            self._push_frame_state(frame)

        if event == "opcode":
            opcode = code_obj.co_code[frame.f_lasti]
            opcode_arg = code_obj.co_code[frame.f_lasti + 1]

            self._print(frame.f_lasti, self.opname[opcode], opcode_arg)

        frame.f_trace_opcodes = True
        return self


def _run_tracer(source_file: Path, ctrl_socket):
    script_file = source_file.absolute()
    record_file = get_record_file(script_file)

    with record_file.open("rb") as rec_f:
        runscript(script_file, Replay(script_file, Records(rec_f), ctrl_socket, False))


def start_player(source_file: Path):
    parent, child = socketpair(type=SOCK_DGRAM)

    pid = fork()
    if pid:  # parent
        child.close()
        return parent

    # child
    parent.close()
    _run_tracer(source_file, child)
    # terminate process here,
    # to avoid returning to caller of of start_player()
    exit(0)
