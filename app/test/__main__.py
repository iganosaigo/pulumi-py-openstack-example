import pulumi
import pulumi_cloudinit as cloud_init
import yaml
from pulumi import StackReference

import utils.basic as utils
from utils.config_helpers import CreateVM

config = CreateVM.get_config()
stack = CreateVM.get_stack_info().env_suffix
org = CreateVM.get_org()

inventory = config.require_object("inventory")

networks_stackref = StackReference(f"{org}/infra.network/{stack}")
keypair_stackref = StackReference(f"{org}/infra.keys/prod")
default_sg_stackref = StackReference(f"{org}/infra.sg.default/prod")

cloud_init_dict = yaml.load(
    utils.read_file("./cloud_init.yaml"),
    Loader=yaml.SafeLoader,
)

ssh_file = utils.get_ssh_public_key()
if ssh_file:
    cloud_init_dict["users"][0]["ssh_authorized_keys"] = f"{ssh_file}"

cloud_init_config = cloud_init.get_config(
    gzip=False,
    base64_encode=True,
    parts=[
        cloud_init.GetConfigPartArgs(
            filename="te",
            content=yaml.dump(cloud_init_dict),
            content_type="text/cloud-config",
        )
    ],
)

instances_output = []
for item in inventory:
    instance = CreateVM(item)
    instance.create_stackrefs(
        network_stackref=networks_stackref,
        keypair_stackref=keypair_stackref if keypair_stackref else None,
        default_sg_stackref=default_sg_stackref,
    )
    instance.set_user_data(cloud_init_config.rendered)
    instance.run_all()

    output = {
        "name": instance.vm.instance.name,
        "address": instance.vm.instance.access_ip_v4,
        "image": instance.vm.instance.image_name,
        "nat": instance.vm_fip.fip.address if instance.vm_nat else None,
        "network": instance.vm.instance.networks[0].name,
    }

    instances_output.append(output)

pulumi.export("instances", instances_output)
pulumi.export("cloud-init", cloud_init_config.rendered)
