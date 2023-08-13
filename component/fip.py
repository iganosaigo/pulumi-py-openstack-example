from pulumi import ComponentResource, Output, ResourceOptions
from pulumi_openstack.compute import (
    FloatingIpAssociate,
    FloatingIpAssociateArgs,
)
from pulumi_openstack.networking import FloatingIp, FloatingIpArgs
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FieldValidationInfo,
    field_validator,
)


class FipConfig(BaseModel, validate_assignment=True):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fip_name: str
    fip_associate_name: str | None = Field(
        validate_default=True,
        default=None,
    )
    pool: Output[str]
    instance_id: Output[str]

    @field_validator("fip_associate_name")
    @classmethod
    def check_fip_associate_name(
        cls, v: str | None, info: FieldValidationInfo
    ) -> str:
        if v:
            return v
        else:
            fip_name = info.data.get("fip_name")
            return f"{fip_name}-associate"


class Fip(ComponentResource):
    def __init__(
        self,
        args: FipConfig,
        opts=None,
    ):
        super().__init__("my:modules:fip", args.fip_name, None, opts)

        self.fip_args = FloatingIpArgs(pool=args.pool)
        self.fip = FloatingIp(
            args.fip_name,
            self.fip_args,
            opts=ResourceOptions(parent=self),
        )

        self.fip_associate_args = FloatingIpAssociateArgs(
            floating_ip=self.fip.address,
            instance_id=args.instance_id,
        )
        self.fip_associate = FloatingIpAssociate(
            args.fip_associate_name,  # type: ignore
            args=self.fip_associate_args,
        )

        self.register_outputs({})
