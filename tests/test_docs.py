import argparse
import re
import unittest
from pathlib import Path

from arc import cli

COMMANDS_DOC = Path(__file__).resolve().parent.parent / "docs" / "commands.md"


def _long_options(parser: argparse.ArgumentParser) -> set[str]:
    return {opt for action in parser._actions for opt in action.option_strings if opt.startswith("--") and opt != "--help"}


class CommandReferenceTests(unittest.TestCase):
    """docs/commands.md must mention every subcommand and long option the CLI defines."""

    def test_reference_covers_cli(self):
        text = COMMANDS_DOC.read_text(encoding="utf-8")
        parser = cli.build_parser()
        options = _long_options(parser)
        sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        commands = set(sub.choices)
        for subparser in sub.choices.values():
            options |= _long_options(subparser)
        # An option counts when it starts a code span, alone or with its argument: `--to` or `--to DIR`.
        missing = sorted({f"arc {c}" for c in commands if f"## arc {c}" not in text}
                         | {o for o in options if not re.search(rf"`{re.escape(o)}[` ]", text)})
        self.assertEqual(missing, [], f"missing from {COMMANDS_DOC.name}")


if __name__ == "__main__":
    unittest.main()
