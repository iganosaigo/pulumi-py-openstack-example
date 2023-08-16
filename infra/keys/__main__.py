import os
import sys
import pathlib
import pulumi
import pulumi_openstack as openstack

directory = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(directory.as_posix())


import component
from utils.basic import get_ssh_public_key

config = component.Config()
stack_info = config.parse_stack()
stack = stack_info.env_suffix

home_key = config.get_bool("home_key")

if home_key:
    ssh_public_key = get_ssh_public_key()
    username = os.path.expanduser("~").rsplit("/")[-1]

    if ssh_public_key:
        keypair_name = f"{stack}-{username}-keypair"
        keypair = openstack.compute.Keypair(
            keypair_name, public_key=ssh_public_key, name=keypair_name
        )
    else:
        pulumi.log.error("SSH file not found!")
        raise

    pulumi.export("keypair", keypair)
