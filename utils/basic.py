import ipaddress as ip
import json
import os
from distutils.util import strtobool
from functools import cache
from typing import Any, Literal, overload

import pulumi
import yaml


@overload
def str_to_address(addr: str, addr_type: Literal["network"]) -> ip.IPv4Network:
    ...


@overload
def str_to_address(addr: str, addr_type: Literal["address"]) -> ip.IPv4Address:
    ...


def str_to_address(addr, addr_type: Literal["network", "address"] = "network"):
    try:
        if addr_type == "network":
            return ip.IPv4Network(addr)
        elif addr_type == "address":
            return ip.IPv4Address(addr)
    except ValueError as e:
        pulumi.log.error("Wrong IP address provided")
        raise e


def make_header(action: str, workspace: str) -> str:
    msg = f"{action} on workspace {workspace}"
    sep = "\n" + len(msg) * "-" + "\n"
    return f"{sep}{msg}{sep}"


def get_leaf_dirs(root_directory: str) -> list[str]:
    result = []

    for dirpath, dirnames, filenames in os.walk(root_directory):
        if {"Pulumi.yaml", "__main__.py"}.issubset(filenames):
            result.append(dirpath)

    return result


def list_values(v) -> list[str | bool | int]:
    return [x.value for x in list(v)]


def create_bool_from_json(v: str | bool | None) -> bool:
    if v is None:
        return True
    elif isinstance(v, str):
        return bool(strtobool(v))
    elif v is bool:
        return v
    else:
        raise ValueError


def create_list_from_json(v: Any) -> list[str]:
    if v is None:
        return []
    elif isinstance(v, str):
        result = json.loads(v)
        assert isinstance(result, list)
        for addr in result:
            assert isinstance(addr, str)
        return result
    elif isinstance(v, list):
        return v
    raise ValueError


def read_file(file: str) -> str:
    with open(file, "r") as f:
        return f.read().strip()


def file_exists(file: str) -> bool:
    if os.path.exists(file):
        return True
    return False


def get_ssh_public_key(ssh_file: str | None = None) -> str | None:
    if ssh_file and file_exists(ssh_file):
        return read_file(ssh_file)

    home_dir = os.path.expanduser("~")
    default_ssh_file = os.path.join(home_dir, ".ssh", "id_rsa.pub")

    if file_exists(default_ssh_file):
        return read_file(default_ssh_file).strip()
    else:
        return None


@cache
def read_pulumi_config(filename: str) -> None | Any:
    try:
        network_yaml = read_file(filename)

    except FileNotFoundError:
        pulumi.log.error(f"Env file {filename} not found")
        return None

    return yaml.safe_load(network_yaml)["config"]
