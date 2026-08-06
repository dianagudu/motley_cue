"""Assurance evaluation: map a user's assurance/MFA claims to a shell tier.

This logic was formerly part of feudalAdapter (a single global
``assurance.require`` expression gating deployment). It now lives in motley_cue,
which has the per-OP context and the full token (userinfo, access-token body,
introspection). Instead of rejecting, the evaluation classifies each user into a
shell *tier* that is passed to feudalAdapter, which maps it to a login shell.

The policy is configured per OP, in the ``[authorisation.<op>]`` sections (with
``[DEFAULT]`` supplying the values an OP does not override) -- see
:class:`motley_cue.mapper.config.ConfigOPAuthZ`.
"""

import logging
import re
from typing import Callable, Dict, Set

from flaat.user_infos import UserInfos

from motley_cue.logsetup import audit
from motley_cue.mapper.config import ConfigAuthorisation, ConfigOPAuthZ, canonical_url
from motley_cue.mapper.exceptions import InternalException

logger = logging.getLogger(__name__)

# Tiers in priority order, highest privilege first.
TIERS = ["full", "limited", "restricted"]

# Tokeniser for the assurance boolean grammar.
_TOKEN_RE = re.compile(r"&|\||\(|\)|[^\s()&|]+")


def parse_requirement(expression: str, prefix: str) -> Callable[[Set[str]], bool]:
    """Parse a boolean assurance expression into a predicate over a set of claim values.

    Grammar: ``E -> E "&" E | E "|" E | "(" E ")" | string``, where ``&`` binds
    stronger than ``|``. A string matches if the assurance set contains it
    verbatim or expanded with ``prefix``; this makes both REFEDS-style URLs and
    bare claim values (e.g. an ``acr`` of ``1``, or an ``amr`` of ``mfa``)
    reachable. Absolute ``http[s]://`` strings are only matched verbatim.
    ``"+"`` matches if the user has any claim at all; ``"*"`` always matches. An
    empty expression never matches.
    """
    if not expression or expression.strip() == "":
        return lambda values: False

    prefix = prefix.rstrip("/") + "/"
    tokens = _TOKEN_RE.findall(expression)

    # Recursive-descent parser building a tree of predicates (ported from feudal).
    def parse_expr(seq):
        expr = parse_disjunction(seq)
        if len(seq) > 0:
            raise ValueError("Trailing tokens while parsing assurance expression")
        return expr

    def parse_disjunction(seq):
        lhs = parse_konjunction(seq)
        return parse_disjunction2(seq, lhs)

    def parse_disjunction2(seq, lhs):
        if len(seq) > 0 and seq[0] == "|":
            seq.pop(0)
            rhs = parse_konjunction(seq)
            return parse_disjunction2(seq, lambda values: lhs(values) or rhs(values))
        return lhs

    def parse_konjunction(seq):
        lhs = parse_primary(seq)
        return parse_konjunction2(seq, lhs)

    def parse_konjunction2(seq, lhs):
        if len(seq) > 0 and seq[0] == "&":
            seq.pop(0)
            rhs = parse_primary(seq)
            return parse_konjunction2(seq, lambda values: lhs(values) and rhs(values))
        return lhs

    def parse_primary(seq):
        if len(seq) > 0 and seq[0] == "(":
            seq.pop(0)
            subexpr = parse_disjunction(seq)
            if len(seq) == 0 or seq.pop(0) != ")":
                raise ValueError("Missing ')' while parsing assurance expression")
            return subexpr
        return parse_assurance(seq)

    def parse_assurance(seq):
        if len(seq) == 0:
            raise ValueError("Unexpected end of assurance expression")
        value = seq.pop(0)
        if value == "+":
            return lambda values: len(values) > 0
        if value == "*":
            return lambda values: True
        if re.match("https?://", value):
            return lambda values: value in values
        # a relative value matches verbatim or expanded with the prefix, so that
        # non-REFEDS claim values (acr = 1, amr = mfa, ...) are reachable too
        prefixed = prefix + value
        return lambda values: value in values or prefixed in values

    return parse_expr(tokens)


class _OPAssurance:
    """Assurance policy of a single OP, with its tier expressions pre-parsed."""

    def __init__(self, op_authz: ConfigOPAuthZ):
        self._op_url = op_authz.op_url
        self._claims = op_authz.assurance_claims
        expressions = {
            "full": op_authz.assurance_based_shell_tier_full,
            "limited": op_authz.assurance_based_shell_tier_limited,
            "restricted": op_authz.assurance_based_shell_tier_restricted,
        }
        self._tier_reqs = {}
        for tier, expression in expressions.items():
            try:
                self._tier_reqs[tier] = parse_requirement(expression, op_authz.assurance_prefix)
            except ValueError as ex:
                raise InternalException(
                    f"Invalid assurance_based_shell_tier_{tier} for OP "
                    f"'{op_authz.op_url}': {expression!r} ({ex})"
                ) from ex
        # Is the feature switched on *for this OP*? Expressions set in [DEFAULT]
        # are inherited by every OP, so a global policy enables all of them,
        # while a policy on one [authorisation.<op>] section leaves the rest
        # alone.
        self._policy_configured = any(str(e).strip() for e in expressions.values())
        # Validate the tier names. An unrecognised tier used to be ignored
        # silently, which fails OPEN: a mistyped max_tier dropped the cap, and a
        # mistyped default_tier was handed to feudalAdapter, which maps any
        # unknown tier to its default (i.e. the *full*) shell. Both end in more
        # privilege than the operator asked for, so refuse to start instead --
        # consistent with how a malformed expression is handled.
        self._default_tier = self._resolve_default_tier(
            op_authz.assurance_based_shell_default_tier, op_authz.op_url
        )
        self._max_tier = self._validated_tier(
            op_authz.assurance_based_shell_max_tier,
            "assurance_based_shell_max_tier",
            op_authz.op_url,
            allow_empty=True,
        )

    def _resolve_default_tier(self, configured: str, op_url: str) -> str:
        """The tier to use when no expression matches.

        An explicit setting always wins. Left unset, it depends on whether this
        OP has an assurance policy at all: without one the feature is off and
        the tier is "full" (i.e. feudalAdapter's default shell, the behaviour
        from before shell tiers existed); with one, it is the least privileged
        tier, so that a policy which never matches cannot silently grant more
        than the operator intended.
        """
        if configured is not None and configured != "":
            return self._validated_tier(configured, "assurance_based_shell_default_tier", op_url)
        if self._policy_configured:
            logger.debug(
                "No assurance_based_shell_default_tier for OP '%s'; a policy is "
                "configured, so unmatched users get the least privileged tier '%s'",
                op_url,
                TIERS[-1],
            )
            return TIERS[-1]
        return TIERS[0]

    @staticmethod
    def _validated_tier(tier: str, option: str, op_url: str, allow_empty: bool = False) -> str:
        """Return `tier`, or raise if it is not one of TIERS.

        `allow_empty` permits "" for options where empty means "unset".
        """
        if allow_empty and (tier is None or tier == ""):
            return ""
        if tier not in TIERS:
            raise InternalException(
                f"Invalid {option} for OP '{op_url}': {tier!r}. "
                f"Must be one of {', '.join(TIERS)}"
                f"{' (or empty)' if allow_empty else ''}."
            )
        return tier

    def _assurance_set(self, user_infos: UserInfos) -> Set[str]:
        """Collect the union of all configured claim values from every available
        token source (userinfo, access-token body, introspection).

        This reads the three source dicts directly instead of going through
        `UserInfos.get`, which returns only the first source that has the claim
        and would hide values carried by the others.
        """
        values: Set[str] = set()
        access_token_info = getattr(user_infos, "access_token_info", None)
        sources = [
            ("user_info", getattr(user_infos, "user_info", None)),
            ("access_token_info.body", getattr(access_token_info, "body", None)),
            ("introspection_info", getattr(user_infos, "introspection_info", None)),
        ]
        for claim in self._claims:
            for source_name, src in sources:
                if not src:
                    continue
                val = src.get(claim)
                if val is None:
                    continue
                found: Set[str] = set()
                if isinstance(val, str):
                    # a claim like `acr` may be a single value or a
                    # space-separated list of class references
                    found.add(val)
                    found.update(val.split())
                elif isinstance(val, (list, tuple, set)):
                    found.update(str(v) for v in val)
                else:
                    found.add(str(val))
                logger.debug("Assurance claim '%s' from %s: %s", claim, source_name, sorted(found))
                values.update(found)
        return values

    def evaluate(self, user_infos: UserInfos) -> str:
        """Return the shell tier for the given user."""
        values = self._assurance_set(user_infos)
        tier = self._default_tier
        for candidate in TIERS:
            req = self._tier_reqs.get(candidate)
            if req is not None and req(values):
                tier = candidate
                break
        capped = self._cap(tier, self._max_tier)
        if capped != tier:
            logger.debug(
                "Capping assurance tier %s to %s (assurance_based_shell_max_tier of %s)",
                tier,
                capped,
                self._op_url,
            )
        logger.debug("Evaluated assurance tier: %s", capped)
        return capped

    @staticmethod
    def _cap(tier: str, max_tier: str) -> str:
        """Lower `tier` to `max_tier` if it exceeds it (lower index = higher privilege)."""
        if not max_tier or max_tier not in TIERS or tier not in TIERS:
            return tier
        if TIERS.index(tier) < TIERS.index(max_tier):
            return max_tier
        return tier


class AssuranceEvaluator:
    """Classifies a user into a shell tier, using their OP's assurance policy.

    All tier expressions are parsed once, at startup, per OP.
    """

    def __init__(self, authorisation: ConfigAuthorisation):
        self._per_op: Dict[str, _OPAssurance] = {
            op_key: _OPAssurance(op_authz)
            for op_key, op_authz in authorisation.all_op_authz.items()
        }
        # For an OP without its own section. Such a user is not authorised
        # anyway, but this keeps the evaluation total -- and it uses the
        # operator's [DEFAULT] policy rather than the built-in defaults, so that
        # a configured catch-all (assurance_based_shell_tier_restricted = *)
        # also covers an unknown OP instead of silently granting "full".
        self._fallback = _OPAssurance(authorisation.default_op_authz)

    def evaluate(self, user_infos: UserInfos) -> str:
        """Return the shell tier for the given user, per their OP's policy."""
        op_key = canonical_url(user_infos.issuer)
        op_assurance = self._per_op.get(op_key)
        if op_assurance is None:
            logger.debug("No assurance configuration for OP %s, using defaults", op_key)
            op_assurance = self._fallback
        tier = op_assurance.evaluate(user_infos)
        # this decides the user's login shell, so record it whatever the log level
        audit(
            logger,
            "Assurance tier '%s' for %s @ %s",
            tier,
            user_infos.subject,
            user_infos.issuer,
        )
        return tier
