from pulumi import ComponentResource, Output, ResourceOptions
from pulumi_cloudinit.get_config import AwaitableGetConfigResult
from pulumi_openstack.compute import Instance, InstanceNetworkArgs
from pydantic import BaseModel, ConfigDict


class VmConfig(BaseModel, validate_assignment=True):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    flavor_id: str
    image_id: str
    key_pair: Output[str] | None = None
    security_groups: list[Output[str]]
    internal_net_id: Output[str] | str
    access_network: bool = True
    fixed_ip: str | None = None
    user_data: str | Output[str] | AwaitableGetConfigResult | None = None


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
        network_args = InstanceNetworkArgs(
            access_network=args.access_network,
            uuid=args.internal_net_id,
            fixed_ip_v4=args.fixed_ip,
        )
        params = {
            "flavor_id": args.flavor_id,
            "image_id": args.image_id,
            "security_groups": args.security_groups,
            "networks": [network_args],
        }
        if args.user_data:
            params["user_data"] = args.user_data
        if args.key_pair:
            params["key_pair"] = args.key_pair

        return params
