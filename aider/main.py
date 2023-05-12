import os
import sys
import argparse
from dotenv import load_dotenv
from aider.coder import Coder
from rich.console import Console


def main(args=None):
    if not args:
        args = sys.argv[1:]

    load_dotenv()
    env_prefix = "AIDER_"
    parser = argparse.ArgumentParser(description="aider - chat with GPT about your code")
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a list of source code files (optional)",
    )
    parser.add_argument(
        "--history-file",
        metavar="HISTORY_FILE",
        default=os.environ.get(f"{env_prefix}HISTORY_FILE", ".aider.history"),
        help=(
            "Specify the chat input history file (default: .aider.history,"
            f" ${env_prefix}HISTORY_FILE)"
        ),
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        default=os.environ.get(f"{env_prefix}MODEL", "gpt-4"),
        help=f"Specify the model to use for the main chat (default: gpt-4, ${env_prefix}MODEL)",
    )
    parser.add_argument(
        "-3",
        action="store_const",
        dest="model",
        const="gpt-3.5-turbo",
        help="Use gpt-3.5-turbo model for the main chat (basically won't work)",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_false",
        dest="pretty",
        help=f"Disable pretty, colorized output (${env_prefix}PRETTY)",
        default=bool(int(os.environ.get(f"{env_prefix}PRETTY", 1))),
    )
    parser.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    parser.add_argument(
        "--no-auto-commits",
        action="store_false",
        dest="auto_commits",
        help=f"Disable auto commit of changes (${env_prefix}AUTO_COMMITS)",
        default=bool(int(os.environ.get(f"{env_prefix}AUTO_COMMITS", 1))),
    )
    parser.add_argument(
        "--show-diffs",
        action="store_true",
        help=f"Show diffs when committing changes (default: False, ${env_prefix}SHOW_DIFFS)",
        default=bool(int(os.environ.get(f"{env_prefix}SHOW_DIFFS", 0))),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Always say yes to every confirmation",
        default=False,
    )
    args = parser.parse_args(args)
    fnames = args.files
    pretty = args.pretty

    coder = Coder(
        args.model, fnames, pretty, args.history_file, args.show_diffs, args.auto_commits, args.yes
    )
    coder.commit(ask=True, prefix="wip: ", which="repo_files")

    if args.apply:
        with open(args.apply, "r") as f:
            content = f.read()
        coder.update_files(content, inp="")
        return

    coder.run()
    console = Console()
    console.clear()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
