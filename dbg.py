#!/usr/bin/env python3
"""
commands:

help   - print help
source - show source code
opcode - show bytecode
next   - next line
step   - next bytecode
vars   - show variables (locals, globals)
stack  - show stack
quit   - exit debugger
"""
from typing import Optional, Iterable, Tuple
import dis
from argparse import ArgumentParser
from pathlib import Path
from enum import Enum
from sys import stdin, stdout, stderr
from itertools import count, chain
from zhukov import decode_frame, Frame
from player import start_player

MAX_SOURCE_ROWS = 20


class ReplaySocket:
    def __init__(self, script_file):
        self._socket = start_player(script_file)

    def get_frame(self) -> Frame:
        response = self._socket.recv(1024 * 32)
        return decode_frame(response)

    def step_line(self):
        self._socket.send(b"line")

    def step_opcode(self):
        self._socket.send(b"opcode")

    def close(self):
        self._socket.close()


class Command:
    name = None
    help_text = None

    def run(self, replay_socket: ReplaySocket):
        raise NotImplementedError()


class HelpCmd(Command):
    name = "help"
    help_text = "print help"


class SourceCmd(Command):
    name = "source"
    help_text = "show source code"


class OpcodeCmd(Command):
    name = "opcode"
    help_text = "show bytecode"


class NextCmd(Command):
    name = "next"
    help_text = "next line"


class StepCmd(Command):
    name = "step"
    help_text = "next bytecode"


class VarsCmd(Command):
    name = "vars"
    help_text = "show variables (locals, globals)"


class FrameCmd(Command):
    name = "frame"
    help_text = "show current frame"


class QuitCmd(Command):
    name = "quit"
    help_text = "exit debugger"


class Commands(Enum):
    HELP = HelpCmd()
    SOURCE = SourceCmd()
    OPCODE = OpcodeCmd()
    NEXT = NextCmd()
    STEP = StepCmd()
    VARS = VarsCmd()
    FRAME = FrameCmd()
    QUIT = QuitCmd()


def err_exit(error_msg):
    stderr.write("%s\n" % error_msg)
    exit(1)


def validate_args(args):
    # make sure we can read the script file
    args.script_file = Path(args.script_file)
    if not args.script_file.is_file():
        err_exit(f"can't read script file '{args.script_file}'")

    return args


def parse_args():
    parser = ArgumentParser(description="replay recording")

    parser.add_argument(
        "script_file", metavar="<script_file>", type=str, action="store"
    )

    return parser.parse_args()


def get_commands():
    stdout.write("(dbg) ")
    stdout.flush()
    line = stdin.readline()

    if not line:
        yield Commands.QUIT
        return

    line = line.strip()
    for command in Commands:
        if command.value.name.startswith(line):
            yield command


def ambiguous_command(commands):
    print("ambiguous command specified:")
    for command in commands:
        print(f"  {command.value.name}")


class SourceFile:
    def __init__(self, frame: Frame):
        self.frame = frame
        self.file = Path(frame.source_file)

    def readable(self):
        return self.file.is_file()

    def get_numbered_lines(self) -> Iterable[Tuple[int, str]]:
        with self.file.open("rt") as f:
            for lineno, line in zip(count(1), f):
                yield lineno, line

    def get_current_line(self) -> Optional[Tuple[int, str]]:
        if not self.readable():
            return None

        for n, line in self.get_numbered_lines():
            if n == self.frame.lineno:
                return n, line

        # the frame.lineno is beyond end of file
        return None


class Opcodes:
    STORE_NAME = dis.opmap["STORE_NAME"]  #  90
    LOAD_CONST = dis.opmap["LOAD_CONST"]  # 100
    LOAD_NAME = dis.opmap["LOAD_NAME"]  # 101
    LOAD_FAST = dis.opmap["LOAD_FAST"]  # 124
    LOAD_METHOD = dis.opmap["LOAD_METHOD"] # 160

    def __init__(self, frame: Frame):
        self.frame = frame

    def _get_arg_note(self, opcode, arg) -> Optional[str]:
        match opcode:
            case self.LOAD_CONST:
                return self.frame.code.consts[arg]
            case self.LOAD_FAST:
                return self.frame.code.varnames[arg]
            case self.STORE_NAME | self.LOAD_NAME | self.LOAD_METHOD:
                return self.frame.code.names[arg]
            case _:
                return None

    def get_opcodes(self):
        code = self.frame.code

        line_regions = chain(code.lines)
        end = -1
        lineno = None

        for i in range(0, len(code.code), 2):
            if i >= end:
                start, end, lineno = next(line_regions)
                if lineno is None:
                    lineno = "?"

            opcode = code.code[i]
            arg = code.code[i + 1]
            arg_note = self._get_arg_note(opcode, arg)
            op_name = dis.opname[opcode]

            yield lineno, i, op_name, arg, arg_note

    def get_current_opcode(self):
        for lineno, i, op_name, arg, arg_note in self.get_opcodes():
            if i == self.frame.lasti:
                return lineno, i, op_name, arg, arg_note


#
# Commands implementation
#


def print_help():
    for command in Commands:
        print(f"{command.value.name:{6}} - {command.value.help_text}")


def goto_next_line(reply_socket: ReplaySocket):
    reply_socket.step_line()
    frame = reply_socket.get_frame()

    current_line = SourceFile(frame).get_current_line()
    if current_line:
        lineno, line = current_line
        print(f"{lineno:{3}} {line}", end="")

    return frame


def goto_next_opcode(reply_socket: ReplaySocket):
    reply_socket.step_opcode()
    frame = reply_socket.get_frame()

    lineno, i, op_name, arg, arg_note = Opcodes(frame).get_current_opcode()
    arg_note = "" if arg_note is None else f" ({arg_note})"
    print(f"{lineno:{5}} {i:{12}} {op_name:{20}} {arg:{3}}{arg_note}")

    return frame


def show_variables(frame: Frame):
    def _print_vars(vars_dict):
        for name, val in vars_dict.items():
            print(f"  {name}: {val}")

    print("globals:")
    _print_vars(frame.globals)
    print("locals:")
    _print_vars(frame.locals)


def show_source(frame: Frame):
    source_file = SourceFile(frame)
    if not source_file.readable():
        print(f"can't read source file '{source_file.file}'")
        return

    start_line = max(1, frame.lineno - (MAX_SOURCE_ROWS // 2))
    end_line = start_line + MAX_SOURCE_ROWS

    for lineno, line in source_file.get_numbered_lines():
        if lineno < start_line:
            continue

        if lineno >= end_line:
            break

        prefix = "-->" if frame.lineno == lineno else lineno
        print(f"{prefix:{3}} {line}", end="")


def show_opcodes(frame: Frame):
    opcodes = Opcodes(frame)

    all_opcodes = []
    lasti_line = None
    prev_line = None
    for lineno, i, op_name, arg, arg_note in opcodes.get_opcodes():
        first_col = ""

        if lineno != prev_line:
            # we are at new source code line
            first_col = lineno

            if prev_line:
                # separate each source code line block by empty line
                # (and don't insert empty line before first block)
                all_opcodes.append("")

            prev_line = lineno

        if i == frame.lasti:
            first_col = "-->"
            lasti_line = len(all_opcodes)

        arg_note = "" if arg_note is None else f" ({arg_note})"
        line = f"{first_col:{5}} {i:{12}} {op_name:{20}} {arg:{3}}{arg_note}"

        all_opcodes.append(line)

    start = max(0, lasti_line - (MAX_SOURCE_ROWS // 2))
    end = min(len(all_opcodes), start + MAX_SOURCE_ROWS)

    for line in all_opcodes[start:end]:
        print(line)


def show_frame(frame):
    def _print_numbered(name, items):
        print(f"  {name}:")
        for i, name in enumerate(items):
            print(f"    {i:2}: {name}")

    print(
        f"f_lineno: {frame.lineno}\n"
        f"f_lasti: {frame.lasti}\n"
        f"f_code:\n"
        f"  co_filename: {frame.code.filename}"
    )
    _print_numbered("co_varnames", frame.code.varnames)
    _print_numbered("co_consts", frame.code.consts)
    _print_numbered("co_names", frame.code.names)


def run_commands(reply_socket: ReplaySocket):
    frame = reply_socket.get_frame()

    while True:
        commands = list(get_commands())

        if len(commands) == 0:
            print("que?")
            continue

        if len(commands) > 1:
            ambiguous_command(commands)
            continue

        command = commands[0]
        match command:
            case Commands.HELP:
                print_help()
            case Commands.SOURCE:
                show_source(frame)
            case Commands.OPCODE:
                show_opcodes(frame)
            case Commands.NEXT:
                frame = goto_next_line(reply_socket)
            case Commands.STEP:
                frame = goto_next_opcode(reply_socket)
            case Commands.VARS:
                show_variables(frame)
            case Commands.FRAME:
                show_frame(frame)
            case Commands.QUIT:
                break
            case _:
                print(f"'{command.value.name}' not implemented")

    print("goodbye")


def main():
    args = validate_args(parse_args())

    reply_socket = ReplaySocket(args.script_file)
    run_commands(reply_socket)
    reply_socket.close()


main()
