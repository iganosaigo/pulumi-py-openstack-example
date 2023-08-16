import pulumi
import sys
import pathlib

directory = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(directory.as_posix())

import component
import utils.config_helpers as helper

config = component.Config()
stack_info = config.parse_stack()

networks = config.require_object("networks")
external_network = helper.get_network_by_name(
    config.require("external_network")
)
default_router = helper.get_router_by_name(config.require("default_router"))

default_dns = config.get_object("default_dns")
if default_dns is None or not isinstance(default_dns, list) or not default_dns:
    default_dns = []

networks_output = []
for net in networks:
    network_admin_state = net.get("network_admin_state_up")
    dns = net.get("dns", default_dns)
    dhcp = net.get("dhcp")
    dhcp_pool = net.get("dhcp_pool")
    router_name = net.get("router")

    if router_name is None:
        router_name = default_router.name

    network_name = f"{stack_info.env_suffix}-{net['name']}"
    subnet_name = f"{network_name}-subnet"
    network_args = component.VpcConfig(
        network_name=network_name,
        subnet_cidr=net["cidr"],
        router_name=router_name,
        subnet_dns=dns,
        subnet_name=subnet_name,
    )

    if network_admin_state is not None:
        network_args.network_admin_state_up = network_admin_state
    if dhcp is not None:
        network_args.subnet_dhcp = dhcp
    if dhcp_pool:
        network_args.subnet_dhcp_pool = dhcp_pool

    net = component.Vpc(network_name, args=network_args)

    output = {
        "network_id": net.network.id,
        "admin_state_up": net.network.admin_state_up,
        "name": net.network.name,
        "subnet": {
            "name": net.subnet.name,
            "id": net.subnet.id,
            "cidr": net.subnet.cidr,
            "dns": net.subnet.dns_nameservers,
            "dhcp": net.subnet.enable_dhcp,
            "dhcp_pool": net.subnet.allocation_pools[0],
        },
    }

    networks_output.append(output)

pulumi.export("networks", networks_output)
pulumi.export("external_network_name", external_network.name)
