from dataclasses import dataclass, field

import pulumi


@dataclass
class StackInfo:
    fullname: str
    stack: str
    project: str
    env_prefix: str = field(init=False)
    env_suffix: str = field(init=False)

    def __post_init__(self):
        self.env_suffix = self.stack.lower()
        self.env_prefix = self.project.lower()


class Config(pulumi.Config):
    def __init__(self, name: str | None = None):
        if name:
            super().__init__(name)
        else:
            super().__init__()

        self.stack = pulumi.get_stack()
        self.project = pulumi.get_project()

        self._name = name

    @property
    def fullname(self) -> str:
        if self._name:
            return f"{self._name}-{self.stack}"
        else:
            self._name = self.project
            return f"{self._name}-{self.stack}"

    def parse_stack(self) -> StackInfo:
        return StackInfo(
            fullname=self.fullname,
            stack=self.stack,
            project=self.project,
        )
