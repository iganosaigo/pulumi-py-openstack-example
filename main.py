import os
import utils.basic as utils

from pulumi import automation as auto
import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    defaults = {
        "action": "preview",
        "env": "dev",
    }
    parser.set_defaults(**defaults)
    parser.add_argument("--env", "-e", help="Environment name")
    parser.add_argument(
        "--action",
        "-a",
        help="Ation to perform",
        choices=["up", "down", "preview"],
    )
    parser.add_argument(
        "--infra-only",
        help="Run only infrastructure",
        action=argparse.BooleanOptionalAction,
    )
    args = parser.parse_args()
    return args


def run_preview(stack: auto.Stack) -> None:
    header = utils.make_header("PREVIEW", stack.workspace.work_dir)
    print(header)
    stack.preview(on_output=print)


def run_down(stack: auto.Stack) -> None:
    header = utils.make_header("DESTROY", stack.workspace.work_dir)
    print(header)
    stack.destroy(on_output=print)


def run_up(stack: auto.Stack) -> None:
    header = utils.make_header("CREATE", stack.workspace.work_dir)
    print(header)
    stack.refresh()
    stack.up(on_output=print)


def main():
    args = parse_args()

    # Work dirs
    root_dir = os.path.dirname(__file__)
    all_work_dirs = utils.get_leaf_dirs(root_dir)
    action = args.action

    # TODO: make more clear two conditions bellow
    # Reversed action beacouse app goes last
    # So it prevents stucking of OpenStack API
    if action == "down":
        all_work_dirs = all_work_dirs[::-1]
    elif args.infra_only and action in ["up", "preview"]:
        all_work_dirs = all_work_dirs[:-1]

    for work_dir in all_work_dirs:
        stack = auto.create_or_select_stack(
            stack_name=args.env, work_dir=work_dir
        )
        if action == "preview":
            run_preview(stack)
        elif action == "down":
            run_down(stack)
        elif action == "up":
            run_up(stack)


if __name__ == "__main__":
    main()
