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


class Model:
    def __init__(self, source_file: Path):
        self.source_file_name = source_file.name
        self.current_line = 1

        with source_file.open() as f:
            self.source_file_lines = f.readlines()

        self.variables = dict(var1=1, var2="hejsan")

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

        return list(_generate_markup())

    def _build_source_code_widget(self):
        self.source_text_widget = Text(self._markup_source_lines(), wrap="ellipsis")
        filler = Filler(self.source_text_widget, valign="top")

        return LineBox(filler)

    def _build_variables_widget(self):
        text = Text(self._markup_variables())
        filler = Filler(text, valign="top")
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

        header = Text(model.source_file_name)

        body = Columns(
            [
                (80, self._build_source_code_widget()),
                self._build_right_panel(),
            ]
        )

        self.frame = Frame(body, header=header, footer=self._build_footer())

    def update(self):
        self.source_text_widget.set_text(self._markup_source_lines())


class Controller:
    def __init__(self, model: Model, viewer: Viewer):
        self.model = model
        self.viewer = viewer

    def _goto_next_line(self):
        self.model.goto_next_line()
        self.viewer.update()

    def handle_input(self, input):
        if not isinstance(input, str):
            # we only process key inputs,
            # which come in as strings
            return

        input = input.lower()
        if input in ("n", " "):
            self._goto_next_line()
            return

        if input in ("q", "esc"):
            raise ExitMainLoop()


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
    main_loop.run()


main()
