#!/usr/bin/env python
from sys import stderr, exit
from pathlib import Path
from argparse import ArgumentParser
from urwid import (
    Text,
    Filler,
    LineBox,
    Padding,
    Pile,
    Columns,
    Frame,
    MainLoop,
    ExitMainLoop,
)
from zhukov import decode_frame
from player import start_player


class Model:
    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.current_line = 1

        with source_file.open() as f:
            self.source_file_lines = f.readlines()

        self.variables = None

    def goto_next_line(self):
        self.current_line += 1


class Viewer:
    PALETTE = [("highlight", "bold", "default"), ("key", "black", "light gray")]

    def _markup_source_lines(self):
        def _generate_markup():
            for num, line in enumerate(self.model.source_file_lines, start=1):
                if num == self.model.current_line:
                    yield ("highlight", line)
                else:
                    yield line

        return list(_generate_markup())

    def _markup_variables(self):
        def _generate_markup():
            for name, val in self.model.variables.items():
                yield ("highlight", name)
                yield f": {val}\n"

        if not self.model.variables:
            # no variables currently
            return ["nada"]

        return list(_generate_markup())

    def _build_source_code_widget(self):
        self.source_text_widget = Text(self._markup_source_lines(), wrap="ellipsis")
        filler = Filler(self.source_text_widget, valign="top")

        return LineBox(filler)

    def _build_variables_widget(self):
        self.variables_text_widget = Text(self._markup_variables(), wrap="ellipsis")
        filler = Filler(self.variables_text_widget, valign="top")
        v_padding = Padding(filler, left=1, right=1)

        return LineBox(v_padding)

    def _build_frames_widget(self):
        quote_text = Text("frames")
        quote_filler = Filler(quote_text, valign="top")
        v_padding = Padding(quote_filler, left=1, right=1)

        return LineBox(v_padding)

    def _build_right_panel(self):
        return Pile([self._build_variables_widget(), self._build_frames_widget()])

    def _build_footer(self):
        return Text(
            [
                ("key", "n"),
                " / ",
                ("key", "space"),
                " next line ",
                ("key", "q"),
                " / ",
                ("key", "esc"),
                " quit",
            ]
        )

    def __init__(self, model: Model):
        self.model = model

        header = Text(model.source_file.name)

        body = Columns(
            [
                (80, self._build_source_code_widget()),
                self._build_right_panel(),
            ]
        )

        self.frame = Frame(body, header=header, footer=self._build_footer())

    def update(self):
        self.source_text_widget.set_text(self._markup_source_lines())
        self.variables_text_widget.set_text(self._markup_variables())


class ReplaySocket:
    def __init__(self):
        self._new_line_cb = None
        self._socket = None

    def start_reply(self, source_file: Path, main_loop: MainLoop, new_line_cb):
        self._new_line_cb = new_line_cb
        self._socket = start_player(source_file)
        main_loop.watch_file(self._socket.fileno(), self)

    def __call__(self):
        response = self._socket.recv(1024 * 32)

        self._new_line_cb(decode_frame(response))

    def step_line(self):
        self._socket.send(b"")

    def close(self):
        self._socket.close()


class Controller:
    def __init__(self, model: Model, viewer: Viewer):
        self.model = model
        self.viewer = viewer
        self.reply_socket = ReplaySocket()

    def handle_input(self, input):
        if not isinstance(input, str):
            # we only process key inputs,
            # which come in as strings
            return

        input = input.lower()
        if input in ("n", " "):
            self.reply_socket.step_line()
            return

        if input in ("q", "esc"):
            raise ExitMainLoop()

    def new_state(self, frame):
        self.model.current_line = frame.lineno
        self.model.variables = frame.locals
        self.viewer.update()

    def start_replay(self, main_loop: MainLoop):
        self.reply_socket.start_reply(self.model.source_file, main_loop, self.new_state)


def err_exit(error_msg):
    stderr.write("%s\n" % error_msg)
    exit(1)


def validate_args(args):
    # make sure we can read the source file
    args.source_file = Path(args.source_file)
    if not args.source_file.is_file():
        err_exit(f"can't read source file {args.source_file}")

    return args


def parse_args():
    parser = ArgumentParser(description="replay recording")

    parser.add_argument(
        "source_file", metavar="<source_file>", type=str, action="store"
    )

    return parser.parse_args()


def main():
    args = validate_args(parse_args())

    model = Model(args.source_file)
    viewer = Viewer(model)
    controller = Controller(model, viewer)

    main_loop = MainLoop(
        viewer.frame,
        viewer.PALETTE,
        unhandled_input=lambda k: controller.handle_input(k),
    )

    controller.start_replay(main_loop)
    main_loop.run()


main()
