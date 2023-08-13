from enum import Enum

from pulumi import ComponentResource, ResourceOptions
from pulumi_openstack.networking import SecGroup, SecGroupRule
from pydantic import BaseModel, Field, FieldValidationInfo, field_validator

from utils.basic import list_values


class Direction(str, Enum):
    INGRESS = "ingress"
    EGRESS = "egress"


class Proto(str, Enum):
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"


class Ethertype(str, Enum):
    IPV4 = "IPv4"


class SgParams(Enum):
    DIRECTIONS = list_values(Direction)
    PROTOCOLS = list_values(Proto)
    ETHERTYPES = list_values(Ethertype)

    # Perhaps not all of them nessesary if
    # This enum stay locally in this file
    DEFAULT_PREFIX = "0.0.0.0/0"
    DEFAULT_PROTOCOL = "tcp"
    DEFAULT_DIRECTION = "ingress"
    DEFAULT_EHTERTYPE = "IPv4"


class SgRuleConfig(BaseModel, validate_assignment=True):
    name: str
    port: int = Field(default=None)
    direction: Direction = Direction.INGRESS
    ethertype: Ethertype = Ethertype.IPV4
    protocol: Proto = Proto.TCP
    remote_ip_prefix: str = SgParams.DEFAULT_PREFIX.value

    @field_validator("port")
    @classmethod
    def check_subnet_name(cls, v: int) -> int | None:
        if v <= 0:
            return None
        else:
            return v


class SgConfig(BaseModel, validate_assignment=True):
    name: str
    description: str | None = Field(default=None, validate_default=True)
    # delete_default_rules: JsonDataBool = Field(default=False)
    delete_default_rules: bool = False
    rules: list[SgRuleConfig] = []

    @field_validator("description")
    @classmethod
    def check_subnet_name(cls, v: str | None, info: FieldValidationInfo) -> str:
        if v:
            return v
        else:
            sg_name = info.data.get("name")
            return f"{sg_name} Security Group"


class Sg(ComponentResource):
    def __init__(
        self,
        name: str,
        args: SgConfig,
        opts=None,
    ):
        super().__init__("my:modules:sg", f"{name}-sg", None, opts)

        self.sg = SecGroup(
            args.name,
            name=args.name,
            description=args.description,
            delete_default_rules=args.delete_default_rules,
            opts=ResourceOptions(parent=self),
        )

        self.sg_rules = self.create_rule_list(args.rules)

        self.register_outputs({})

    def create_rule_list(
        self,
        args: list[SgRuleConfig],
    ) -> list[SecGroupRule]:
        result = []
        for rule in args:
            sg_rule = SecGroupRule(
                rule.name,
                security_group_id=self.sg.id,
                **rule.model_dump(exclude={"name", "port"}),
                port_range_max=rule.port,
                port_range_min=rule.port,
                opts=ResourceOptions(
                    parent=self,
                    delete_before_replace=True,
                ),
            )

            result.append(sg_rule)

        return result
