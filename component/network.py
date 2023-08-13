from typing import Any

from pulumi import ComponentResource, ResourceOptions
from pulumi_openstack import networking
from pulumi_openstack.networking import AwaitableGetRouterResult
from pulumi_openstack.networking.network import SubnetAllocationPoolArgs
from pydantic import (
    BaseModel,
    Field,
    FieldValidationInfo,
    field_validator,
    model_validator,
)

from utils.basic import str_to_address


class VpcConfig(BaseModel, validate_assignment=True):
    network_name: str
    network_admin_state_up: bool = True
    subnet_name: str | None = Field(default=None, validate_default=True)
    subnet_cidr: str
    subnet_dns: list[str] | None = None
    subnet_dhcp: bool = True
    subnet_dhcp_pool: list[str] | None = None
    router_name: str

    @model_validator(mode="after")
    def check_values(self) -> "VpcConfig":
        # Check subnet cidr
        subnet_cidr = str_to_address(self.subnet_cidr, addr_type="network")
        assert subnet_cidr.prefixlen == 24, "Subnet cidr prefix must be /24"

        # Check DNS
        subnet_dns = self.subnet_dns
        if subnet_dns:
            assert len(subnet_dns) >= 2, "Provide at least 2 DNS address"
            for dns in subnet_dns:
                str_to_address(dns, addr_type="address")

        # Check DHCP pool
        subnet_dhcp = self.subnet_dhcp
        subnet_dhcp_pool = self.subnet_dhcp_pool
        if subnet_dhcp:
            if subnet_dhcp_pool:
                assert len(subnet_dhcp_pool) == 2
                testing_pool = dhcp_start, dhcp_end = [
                    str_to_address(addr, addr_type="address")
                    for addr in subnet_dhcp_pool
                ]
                assert dhcp_start <= dhcp_end, "DHCP start must be lower end"
                for addr in testing_pool:
                    assert (
                        addr in subnet_cidr
                    ), "DHCP addresses must be within network cidr"
            else:
                address_list = list(subnet_cidr.hosts())
                dhcp_start = str(address_list[10])
                dhcp_end = str(address_list[99])
                self.subnet_dhcp_pool = [dhcp_start, dhcp_end]

        return self

    @field_validator("subnet_name")
    @classmethod
    def check_subnet_name(cls, v: str | None, info: FieldValidationInfo) -> str:
        if v:
            return v
        else:
            subnet_name = info.data.get("network_name")
            return f"{subnet_name}-subnet"


class Vpc(ComponentResource):
    def __init__(
        self,
        name: str,
        args: VpcConfig,
        opts=None,
    ):
        super().__init__("my:modules:vpc", f"{name}-vpc", None, opts)
        subnet_name = args.subnet_name
        router_iface_name = f"{name}-router-iface"

        self.network = networking.Network(
            args.network_name,
            name=args.network_name,
            admin_state_up=args.network_admin_state_up,
            opts=ResourceOptions(parent=self),
        )

        subnet_params = self.create_subnet_params(args)

        self.subnet = networking.Subnet(
            subnet_name,  # type: ignore
            name=subnet_name,
            network_id=self.network.id,
            **subnet_params,
            opts=ResourceOptions(parent=self),
        )

        self.router = self.get_router(args.router_name)

        self.router_iface = networking.RouterInterface(
            router_iface_name,
            router_id=self.router.id,
            subnet_id=self.subnet.id,
            opts=ResourceOptions(parent=self, delete_before_replace=True),
        )

        self.register_outputs({})

    def get_router(self, router_name: str) -> AwaitableGetRouterResult:
        return networking.get_router(name=router_name)

    def create_allocation_pool(
        self,
        start: str,
        end: str,
    ) -> SubnetAllocationPoolArgs:
        return networking.SubnetAllocationPoolArgs(
            start=start,
            end=end,
        )

    def create_subnet_params(self, args: VpcConfig) -> dict[str, Any]:
        subnet_params: dict[str, Any] = {
            "cidr": args.subnet_cidr,
            "enable_dhcp": args.subnet_dhcp,
        }

        if args.subnet_dns:
            subnet_params.update({"dns_nameservers": args.subnet_dns})

        if args.subnet_dhcp:
            pool_start, pool_end = args.subnet_dhcp_pool  # type: ignore
            self.dhcp_pool = self.create_allocation_pool(
                start=pool_start,
                end=pool_end,
            )

            subnet_params.update({"allocation_pools": [self.dhcp_pool]})

        return subnet_params
