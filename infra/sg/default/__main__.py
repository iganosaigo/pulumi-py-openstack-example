import pulumi
import sys
import pathlib

directory = pathlib.Path(__file__).resolve().parents[3]
sys.path.append(directory.as_posix())

import component
import utils.config_helpers as helper

config = component.Config()
stack_info = config.parse_stack()
stack = stack_info.env_suffix

service_name = f"{stack}-sg-default"

sg_rules = config.get_object(
    "sg_rules",
    config.require_object("default_sg_rules"),
)
assert isinstance(sg_rules, list)

sg_rules_config = helper.CreateSgRulesConfig(
    name=f"{service_name}-rule",
    config=config,
).create_config()

sg_args = helper.CreateSgConfig(
    name=f"{service_name}",
    config=config,
    sg_rules=sg_rules_config,
).create_config()

sg = component.Sg(service_name, args=sg_args)

pulumi.export("sg", sg)
