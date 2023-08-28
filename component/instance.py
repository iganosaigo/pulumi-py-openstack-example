from pulumi import ComponentResource, Output, ResourceOptions
from pulumi_cloudinit.get_config import AwaitableGetConfigResult
from pulumi_openstack.compute import (
    Instance,
    InstanceNetworkArgs,
    InstanceBlockDeviceArgs,
)
from pydantic import BaseModel, ConfigDict


class VmConfig(BaseModel, validate_assignment=True):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    flavor_id: str
    image_id: str
    boot_volume: int | None = None
    key_pair: Output[str] | None = None
    security_groups: list[Output[str]]
    internal_net_id: Output[str] | str
    access_network: bool = True
    fixed_ip: str | None = None
    user_data: str | Output[str] | AwaitableGetConfigResult | None = None
    secondary_iface: bool | None = None


class Vm(ComponentResource):
    def __init__(
        self,
        name: str,
        args: VmConfig,
        opts=None,
    ):
        super().__init__("my:modules:instance", name, None, opts)
        params = self.create_instance_params(args)

        self.instance = Instance(
            name,
            **params,
            name=name,
            opts=ResourceOptions(
                parent=self,
                ignore_changes=["image_id", "user_data"],
            ),
        )

        self.register_outputs({})

    def create_instance_params(self, args: VmConfig):
        primary_network_args = InstanceNetworkArgs(
            access_network=args.access_network,
            uuid=args.internal_net_id,
            fixed_ip_v4=args.fixed_ip,
        )

        network_args = [primary_network_args]

        if args.secondary_iface is not None:
            secondary_network_args = InstanceNetworkArgs(
                access_network=False,
                uuid=args.internal_net_id,
            )
            network_args.append(secondary_network_args)
            # TODO: Take care with 2nd iface!!!!!!!
            # network_args.insert(0, secondary_network_args)

        params = {
            "flavor_id": args.flavor_id,
            "security_groups": args.security_groups,
            "networks": network_args,
        }
        if args.user_data:
            params["user_data"] = args.user_data
        if args.key_pair:
            params["key_pair"] = args.key_pair

        if args.boot_volume:
            boot_volume = InstanceBlockDeviceArgs(
                uuid=args.image_id,
                source_type="image",
                boot_index=0,
                volume_size=args.boot_volume,
                delete_on_termination=True,
                destination_type="volume",
            )
            params["block_devices"] = [boot_volume]
        else:
            params["image_id"] = args.image_id

        return params
