import os
from functools import cache
from typing import Any

import pulumi
import pulumi_openstack as openstack
from pulumi import Output, StackReference
from pulumi_cloudinit import AwaitableGetConfigResult
from pulumi_openstack.compute import AwaitableGetFlavorResult
from pulumi_openstack.images import AwaitableGetImageResult
from pulumi_openstack.networking import (
    AwaitableGetNetworkResult,
    AwaitableGetRouterResult,
)

import component
import utils.basic as utils
from component.config import StackInfo
from component.security_group import SgParams


@cache
def get_flavor_by_name(
    flavor_name: str,
) -> AwaitableGetFlavorResult | None:
    try:
        return openstack.compute.get_flavor(name=flavor_name)
    except Exception:
        pulumi.log.error("Flavor {} not found".format(flavor_name))
    return


@cache
def get_image_by_name(image_name: str) -> AwaitableGetImageResult | None:
    try:
        return openstack.images.get_image(name=image_name)
    except Exception:
        pulumi.log.error("Image {} not found".format(image_name))
    return


@cache
def get_network_by_name(name: str) -> AwaitableGetNetworkResult:
    return openstack.networking.get_network(name=name)


@cache
def get_router_by_name(name: str) -> AwaitableGetRouterResult:
    return openstack.networking.get_router(name=name)


class CreateVM:
    config = component.Config()
    stack_info = config.parse_stack()
    stack = stack_info.env_suffix
    proj = stack_info.env_prefix
    org = "organization"

    def __init__(self, vm_obj):
        self.vm_obj = vm_obj

    def create_stackrefs(
        self,
        *,
        network_stackref: StackReference,
        default_sg_stackref: StackReference,
        keypair_stackref: StackReference | None = None,
    ) -> None:
        self.network_stackref = network_stackref
        self.default_sg_stackref = default_sg_stackref
        if keypair_stackref:
            self.keypair_stackref = keypair_stackref

    def set_user_data(
        self, user_data: str | Output[str] | AwaitableGetConfigResult
    ):
        self.user_data = user_data

    def run_all(self):
        self.init_params(self.vm_obj)

        self.vm_args = self.create_config()
        self.create_vm(self.vm_args)

        if self.vm_nat:
            self.create_nat(self.vm)

    def init_params(self, vm_obj) -> None:
        # TODO: Perhaps it's quite unoptimal to make required
        # default params. Leave it for now.
        self.default_network = self.config.require("default_network")
        self.default_image = self.config.require("default_image")
        self.default_flavor = self.config.require("default_flavor")

        self.vm_name = vm_obj["host"]
        self.vm_net = vm_obj.get("network", self.default_network)
        self.vm_nat = vm_obj.get("nat")
        self.vm_flavor = vm_obj.get("flavor")
        self.vm_image = vm_obj.get("image")

        self.network_name = f"{self.stack}-{self.vm_net}"

        self.vm_image_id = self.get_image().id
        self.vm_flavor_id = self.get_flavor().id

        self.vm_fixed_ip = vm_obj.get("fixed_ip")
        if self.vm_fixed_ip:
            self.validate_addresses("../../infra/network")

    @classmethod
    def get_config(cls) -> component.Config:
        return cls.config

    @classmethod
    def get_stack_info(cls) -> StackInfo:
        return cls.stack_info

    @classmethod
    def get_org(cls) -> str:
        return cls.org

    def validate_addresses(self, config_dir: str) -> None:
        network_env = self.read_pulumi_config(config_dir)
        if network_env is None:
            pulumi.log.warn(
                f"IP address {self.vm_fixed_ip} for vm {self.vm_name}"
                " not validated"
            )
        else:
            network_env = network_env["networks"]
            cidr: str | None = next(
                (
                    item["cidr"]
                    for item in network_env
                    if item["name"] == self.vm_net
                ),
                None,
            )
            if cidr is None:
                pulumi.log.error(
                    "CIDR for network {} not found!".format(self.vm_net)
                )
                raise ValueError

            net_cidr = utils.str_to_address(cidr, addr_type="network")
            vm_addr = utils.str_to_address(
                self.vm_fixed_ip, addr_type="address"
            )
            assert vm_addr in net_cidr, "VM ip {} for {} not in CIDR {}".format(
                vm_addr, self.vm_name, net_cidr
            )

    def create_config(self) -> component.VmConfig:
        sg_name = self.get_output_default_sg().apply(
            lambda sg: sg["sg"]["name"]
        )
        internal_net_id = get_network_by_name(self.network_name).id

        result = component.VmConfig(
            name=self.vm_name,
            flavor_id=self.vm_flavor_id,
            image_id=self.vm_image_id,
            security_groups=[sg_name],
            internal_net_id=internal_net_id,
        )

        if self.vm_fixed_ip:
            result.fixed_ip = self.vm_fixed_ip

        if self.user_data:
            result.user_data = self.user_data
        elif self.keypair_stackref:
            key_pair_id = self.get_output_keypair().apply(lambda key: key["id"])
            result.key_pair = key_pair_id

        return result

    def get_image(
        self, image_name: None | str = None
    ) -> AwaitableGetImageResult:
        if image_name:
            vm_image = image_name
        if self.vm_image:
            vm_image = self.vm_image
        else:
            vm_image = self.default_image

        vm_image = get_image_by_name(vm_image)
        assert vm_image

        return vm_image

    def get_flavor(
        self, flavor_name: str | None = None
    ) -> AwaitableGetFlavorResult:
        if flavor_name:
            vm_flavor = flavor_name
        if self.vm_flavor:
            vm_flavor = self.vm_flavor
        else:
            vm_flavor = self.default_flavor

        vm_flavor = get_flavor_by_name(vm_flavor)
        assert vm_flavor

        return vm_flavor

    def get_stackref_output(
        self,
        stackref: StackReference,
        parameter: str,
    ) -> Output[Any]:
        return stackref.get_output(parameter)

    def get_output_default_sg(self) -> Output[Any]:
        return self.get_stackref_output(self.default_sg_stackref, "sg")

    def get_output_keypair(self) -> Output[Any]:
        return self.get_stackref_output(self.keypair_stackref, "keypair")

    def get_output_external_net(self) -> Output[Any]:
        return self.get_stackref_output(
            self.network_stackref, "external_network_name"
        )

    def read_pulumi_config(self, filename) -> Any:
        filename = os.path.join(filename, f"Pulumi.{self.stack}.yaml")
        return utils.read_pulumi_config(filename)

    def create_vm(self, args: component.VmConfig):
        self.vm = component.Vm(f"{self.stack}-vm-{self.vm_name}", args=args)

    def create_nat(self, vm):
        self.fip_args = component.FipConfig(
            pool=self.get_output_external_net(),
            fip_name=f"{self.stack}-fip-{self.vm_name}",
            fip_associate_name=f"{self.stack}-fip-associate-{self.vm_name}",
            instance_id=vm.instance.id,
        )
        self.vm_fip = component.Fip(
            args=self.fip_args,
        )


class CreateSgRulesConfig:
    def __init__(
        self,
        *,
        name: str,
        config: pulumi.Config,
        rules: dict | None = None,
    ):
        self.name = name
        self.config = config

        if rules:
            self.sg_rules = rules
        else:
            self.sg_rules = config.get_object("default_sg_rules")

    def create_port_name(self, port: int) -> str:
        return f"-{port}" if port > 0 else ""

    def create_rule_config(
        self,
        rule: dict[str, Any],
    ) -> component.SgRuleConfig:
        port = rule["port"]
        port_name = self.create_port_name(port)
        direction = rule.get("direction", SgParams.DEFAULT_DIRECTION.value)
        protocol = rule.get("protocol", SgParams.DEFAULT_PROTOCOL.value)
        ethertype = rule.get("ethertype")
        remote_prefix = rule.get("remote_prefix")

        sg_rule_name = f"{self.name}-{direction}-{protocol}{port_name}"

        result = component.SgRuleConfig(
            name=sg_rule_name,
            port=port,
            direction=direction,  # type: ignore
            protocol=protocol,  # type: ignore
        )

        if ethertype:
            result.ethertype = ethertype
        if remote_prefix:
            result.remote_ip_prefix = remote_prefix

        return result

    def create_config(self) -> list[component.SgRuleConfig]:
        if not self.sg_rules:
            return []

        result = []
        for rule in self.sg_rules:
            rule_config = self.create_rule_config(rule)
            result.append(rule_config)

        return result


class CreateSgConfig:
    def __init__(
        self,
        *,
        name: str,
        sg_rules: list[component.SgRuleConfig],
        config: pulumi.Config,
    ):
        self.name = name
        self.sg_rules = sg_rules
        self.config = config

        self.description = config.get("description")
        self.delete_default_rules = config.get_bool("delete_default_rules")

    def create_config(self) -> component.SgConfig:
        result = component.SgConfig(name=self.name, rules=self.sg_rules)

        if self.description:
            result.description = self.description
        if self.delete_default_rules:
            result.delete_default_rules = self.delete_default_rules

        return result
