"""Utility helpers to validate environment credentials for Vendedor360.

This module centralises the logic required to verify that all mandatory
credentials are available before the orchestrator attempts to execute an
agent. Each agent may require one or more environment variables and in some
cases at least one variable from a group (e.g. ``MP_TICKET`` *or*
``MP_SESSION_COOKIE``).

The :class:`CredentialValidator` class performs the validation and returns a
structured report that can be consumed by the orchestrator to decide whether a
step should run or be skipped. The data classes are intentionally lightweight so
that they can also be reused in tests if needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
import os


@dataclass(frozen=True)
class CredentialRequirement:
    """Describe a set of environment variables required for a feature."""

    name: str
    env_vars: Sequence[str]
    mode: str = "all"
    optional: bool = False
    hint: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"all", "any"}:
            raise ValueError("mode must be 'all' or 'any'")
        if not self.env_vars:
            raise ValueError("env_vars must contain at least one item")


@dataclass
class CredentialStatus:
    """Represents the evaluation of a single requirement."""

    requirement: CredentialRequirement
    present: Sequence[str]
    missing: Sequence[str]
    satisfied: bool

    @property
    def optional(self) -> bool:
        return self.requirement.optional


@dataclass
class ValidationReport:
    """Aggregate result of credential validation."""

    statuses: Sequence[CredentialStatus]

    @property
    def ok(self) -> bool:
        """Return ``True`` if every mandatory requirement is satisfied."""

        for status in self.statuses:
            if not status.satisfied and not status.optional:
                return False
        return True

    @property
    def missing_variables(self) -> list[str]:
        """Flatten the missing mandatory environment variables."""

        missing: list[str] = []
        for status in self.statuses:
            if not status.satisfied and not status.optional:
                missing.extend(status.missing)
        return missing

    def summary(self) -> str:
        """Return a human readable summary of missing credentials."""

        messages: list[str] = []
        for status in self.statuses:
            if status.satisfied or status.optional:
                continue
            requirement = status.requirement
            hint = f" ({requirement.hint})" if requirement.hint else ""
            if requirement.mode == "any":
                targets = " o ".join(requirement.env_vars)
                messages.append(f"{requirement.name}: define {targets}{hint}")
            else:
                targets = ", ".join(requirement.env_vars)
                messages.append(f"{requirement.name}: falta {targets}{hint}")
        return "; ".join(messages)


class CredentialValidator:
    """Validate credentials stored in environment variables."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ if environ is not None else os.environ

    def _check(self, requirement: CredentialRequirement) -> CredentialStatus:
        present = [var for var in requirement.env_vars if self._environ.get(var)]
        missing = [var for var in requirement.env_vars if not self._environ.get(var)]
        if requirement.mode == "all":
            satisfied = not missing
        else:  # mode == "any"
            satisfied = bool(present)
        if requirement.optional and not satisfied:
            # Optional credentials are informative but do not fail the report.
            satisfied = True
        return CredentialStatus(
            requirement=requirement,
            present=present,
            missing=missing,
            satisfied=satisfied,
        )

    def validate(self, requirements: Iterable[CredentialRequirement]) -> ValidationReport:
        """Validate a sequence of credential requirements."""

        statuses = [self._check(req) for req in requirements]
        return ValidationReport(statuses=statuses)

    def check(self, *requirements: CredentialRequirement) -> ValidationReport:
        """Convenience wrapper calling :meth:`validate`."""

        return self.validate(requirements)
