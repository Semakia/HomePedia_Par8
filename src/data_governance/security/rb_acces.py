"""
Role-Based Access Control enforcement for the HOMEPEDIA

Turns the '''policies/access_policies.yml''' file into a set of rules
 that can be used to enforce access control on the HOMEPEDIA.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

# access_policies lives one directoty up
_RULES_PATH = (
    Path(__file__).resolve().parent.parent / "policies" / "access_policies.yml"
)

Action = str  # "read" | "write" | "delete"


def _matches(pattern: str, resource: str) -> bool:
    """
    Check if a resource matches a pattern, where the pattern can contain
    wildcards (*).
    """
    pattern = pattern.split(".")
    resource = resource.split(".")
    if len(pattern) != len(resource):
        return False
    return all(p == r or p == "*" for p, r in zip(pattern, resource))


@dataclass
class AccessControl:
    """
    In memory view of RBAC policy
    """

    # role -> list of (resource_pattern, allowed_actions)
    roles: dict[str, list[tuple[str, frozenset[Action]]]]

    @classmethod
    def load(
        cls,
        path: Path | str = _RULES_PATH
    ) -> AccessControl:
        """Load the access control rules from a YAML file."""
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        roles: dict[str, list[tuple[str, frozenset[Action]]]] = {}
        for role, spec in (doc.get("roles", {}).items()):
            perms = [
                (pattern["resource"], frozenset(pattern.get("actions", [])))
                for pattern in spec.get("permissions", [])
            ]
            roles[role] = perms

        return cls(roles)

    def can(self, role: str, resource: str, action: Action) -> bool:
        """Check if a role can perform an action on a resource."""
        for pattern, actions in self.roles.get(role, []):
            if action in actions and _matches(pattern, resource):
                return True
        return False

    def allowed_resources(
        self,
        role: str,
        action: Action
    ) -> list[str]:
        """Get a list of resources that a role can perform an action on."""
        resources = []
        for pattern, actions in self.roles.get(role, []):
            if action in actions:
                resources.append(pattern)
        return resources

    def resuire(
        self,
        role: str,
        resource: str,
        action: Action
    ) -> None:
        """Raise an exception if a role cannot perform an action on a resource."""
        if not self.can(role, resource, action):
            raise PermissionError(
                f"Role '{role}' is not allowed to {action} '{resource}'"
    )

    # Convenience CLI : 'python -m src.data_governance.security.rb_acces check <role> <resource> <action>'
    if __name__ == "__main__":
        import sys

        ac = AccessControl.load()
        if len(sys.argv) == 4:
            role, resource, action = sys.argv[1:4]
            ok = ac.can(role, resource, action)
            print(f"{role} {action} {resource} -> {'ALLOW' if ok else 'DENY'}")
            sys.exit(0 if ok else 1)
        # No args: print the full matrix.
        for role in sorted(ac.roles):
            for action in ("read", "write", "delete"):
                res = ac.allowed_resources(role, action)
                if res:
                    print(f"{role:20s} {action:6s} {', '.join(res)}")