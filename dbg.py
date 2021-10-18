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
from argparse import ArgumentParser
from pathlib import Path
from enum import Enum
from sys import stdin, stdout, stderr
from itertools import count
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


class Help(Command):
    name = "help"
    help_text = "print help"


class Source(Command):
    name = "source"
    help_text = "show source code"


class Opcode(Command):
    name = "opcode"
    help_text = "show bytecode"


class Next(Command):
    name = "next"
    help_text = "next line"


class Step(Command):
    name = "step"
    help_text = "next bytecode"


class Vars(Command):
    name = "vars"
    help_text = "show variables (locals, globals)"


class Stack(Command):
    name = "stack"
    help_text = "show stack"


class Quit(Command):
    name = "quit"
    help_text = "exit debugger"


class Commands(Enum):
    HELP = Help()
    SOURCE = Source()
    OPCODE = Opcode()
    NEXT = Next()
    STEP = Step()
    VARS = Vars()
    STACK = Stack()
    QUIT = Quit()


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
    return reply_socket.get_frame()


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

        if lineno > end_line:
            break

        prefix = "-->" if frame.lineno == lineno else lineno
        print(f"{prefix:{3}} {line}", end="")


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
            case Commands.NEXT:
                frame = goto_next_line(reply_socket)
            case Commands.STEP:
                frame = goto_next_opcode(reply_socket)
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
