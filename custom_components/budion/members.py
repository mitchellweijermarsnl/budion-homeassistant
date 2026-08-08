"""Family member helpers for Budion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CHILD_ROLES: frozenset[str] = frozenset({"teen", "child", "young_child"})


@dataclass
class ChildMember:
    """A wallet-eligible child in the family."""

    membership_id: int
    name: str
    role: str
    role_label: str
    avatar_url: str | None = None
    wallet_balance: int = 0
    wallet_reserved: int = 0
    wallet_total: int = 0
    tasks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def open_task_count(self) -> int:
        """Return the number of open tasks."""
        return sum(1 for task in self.tasks if not task.get("is_completed"))


def member_name(member: dict[str, Any]) -> str:
    """Return a display name for a family member."""
    person = member.get("person")
    if isinstance(person, str) and person.strip():
        return person.strip()
    if isinstance(person, dict):
        return (
            person.get("full_name")
            or person.get("first_name")
            or member.get("role_label")
            or "Kind"
        )
    return (
        member.get("full_name")
        or member.get("first_name")
        or member.get("role_label")
        or "Kind"
    )


def task_assignee_name(member: dict[str, Any] | None) -> str | None:
    """Return the assignee name from a today's-task member payload."""
    if not member:
        return None
    person = member.get("person")
    if isinstance(person, str) and person.strip():
        return person.strip()
    if isinstance(person, dict):
        name = person.get("full_name") or person.get("first_name")
        if name:
            return name
    return member.get("full_name") or member.get("first_name")


def is_child_member(member: dict[str, Any]) -> bool:
    """Return whether a member should get child sensors."""
    return member.get("role") in CHILD_ROLES


def build_children(
    members: list[dict[str, Any]],
    wallets: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> list[ChildMember]:
    """Build child member models from API payloads."""
    wallets_by_membership = {
        wallet.get("membership_id"): wallet for wallet in wallets if wallet.get("membership_id")
    }

    children: list[ChildMember] = []
    for member in members:
        if not is_child_member(member):
            continue

        membership_id = member["id"]
        person = member.get("person") or {}
        wallet = wallets_by_membership.get(membership_id, {})
        member_tasks = [
            task for task in tasks if task.get("membership_id") == membership_id
        ]

        children.append(
            ChildMember(
                membership_id=membership_id,
                name=member_name(member),
                role=member.get("role", ""),
                role_label=member.get("role_label", ""),
                avatar_url=person.get("avatar_url"),
                wallet_balance=int(wallet.get("balance") or 0),
                wallet_reserved=int(wallet.get("reserved") or 0),
                wallet_total=int(wallet.get("total") or wallet.get("balance") or 0),
                tasks=member_tasks,
            )
        )

    children.sort(key=lambda child: child.name.lower())
    return children


def tasks_summary(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a simplified task list for sensor attributes."""
    summary: list[dict[str, Any]] = []
    for item in tasks:
        task = item.get("task") or {}
        summary.append(
            {
                "title": task.get("title"),
                "scheduled_for": item.get("scheduled_for"),
                "is_completed": item.get("is_completed"),
                "coin_reward": task.get("coin_reward"),
            }
        )
    return summary
