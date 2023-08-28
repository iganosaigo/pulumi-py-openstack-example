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
        choices=["up", "destroy", "preview"],
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


def run_destroy(stack: auto.Stack) -> None:
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
    action = args.action

    # Work dirs
    root_dir = os.path.dirname(__file__)
    all_work_dirs = utils.get_leaf_dirs(root_dir)
    infra_work_dirs = [
        x for x in all_work_dirs if x.startswith(f"{root_dir}/infra")
    ]
    app_exclude = [f"{root_dir}/app/test"] # No need app/test in set

    app_work_dirs = [
        x for x in all_work_dirs if x not in set(app_exclude + infra_work_dirs)
    ]

    # Need order - we remove apps first that depends on infra
    # So it prevents stucking of OpenStack API
    if action == "destroy":
        work_dirs = app_work_dirs.copy()
        work_dirs.extend(infra_work_dirs)
    elif args.infra_only and action in ["up", "preview"]:
        work_dirs = infra_work_dirs
    else:
        work_dirs = infra_work_dirs
        work_dirs.extend(app_work_dirs)

    for work_dir in work_dirs:
        stack = auto.create_or_select_stack(
            stack_name=args.env, work_dir=work_dir
        )
        if action == "preview":
            run_preview(stack)
        elif action == "destroy":
            run_destroy(stack)
        elif action == "up":
            run_up(stack)


if __name__ == "__main__":
    main()
