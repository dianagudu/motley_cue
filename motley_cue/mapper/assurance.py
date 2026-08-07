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
from typing import Callable, Dict, Set, Tuple

from flaat.user_infos import UserInfos

from motley_cue.logsetup import audit
from motley_cue.mapper.config import ConfigAuthorisation, ConfigOPAuthZ, canonical_url
from motley_cue.mapper.exceptions import InternalException

logger = logging.getLogger(__name__)

# Tiers in priority order, highest privilege first.
TIERS = ["full", "limited", "restricted"]

# Tokeniser for the assurance boolean grammar.
_TOKEN_RE = re.compile(r"&|\||\(|\)|[^\s()&|]+")


class _Expression:
    """A parsed assurance expression.

    Callable exactly like the bare predicate it replaced -- ``expr(values)``
    returns a bool -- but it also keeps the atoms it was built from, so the
    evaluator can report which individual tokens were looked for and which of
    them the user actually had.

    That matters because a tier which fails to match is otherwise completely
    opaque: the only observable output is the tier that came out at the end,
    with no indication of whether the expression was wrong, the claim was
    missing, or the OP simply renamed something.
    """

    def __init__(self, source: str, predicate, atoms):
        self.source = source
        self._predicate = predicate
        # (token, expanded_form_or_None), in the order written
        self.atoms = atoms

    def __call__(self, values: Set[str]) -> bool:
        return self._predicate(values)

    def explain(self, values: Set[str]) -> str:
        """Per-token breakdown of this expression against `values`, for logging.

        Shows both forms a relative token was tried as, which is the usual
        surprise: `profile/cappuccino` does not resolve under an
        assurance_prefix of the REFEDS root, `assurance/profile/cappuccino`
        does.
        """
        if not self.atoms:
            return "no tokens"
        parts = []
        for token, expanded in self.atoms:
            if token == "+":
                parts.append(f"'+' (any claim present) = {bool(values)}")
            elif token == "*":
                parts.append("'*' (always) = True")
            elif token in values:
                parts.append(f"{token!r} = True")
            elif expanded is not None and expanded in values:
                parts.append(f"{token!r} = True (matched as {expanded!r})")
            elif expanded is not None:
                parts.append(f"{token!r} = False (tried {token!r} and {expanded!r})")
            else:
                parts.append(f"{token!r} = False")
        return "; ".join(parts)


def parse_requirement(expression: str, prefix: str) -> Callable[[Set[str]], bool]:
    """Parse a boolean assurance expression into a predicate over a set of claim values.

    Grammar: ``E -> E "&" E | E "|" E | "(" E ")" | string``, where ``&`` binds
    stronger than ``|``. A string matches if the assurance set contains it
    verbatim or expanded with ``prefix``; this makes both REFEDS-style URLs and
    bare claim values (e.g. an ``acr`` of ``1``, or an ``amr`` of ``mfa``)
    reachable. Absolute ``http[s]://`` strings are only matched verbatim.
    ``"+"`` matches if the user has any claim at all; ``"*"`` always matches. An
    empty expression never matches.

    Returns an :class:`_Expression`, which is callable and returns a bool, and
    additionally carries the parsed atoms so the result can be explained.
    """
    if not expression or expression.strip() == "":
        return _Expression(expression, lambda values: False, [])

    prefix = prefix.rstrip("/") + "/"
    tokens = _TOKEN_RE.findall(expression)
    atoms = []

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
            atoms.append((value, None))
            return lambda values: len(values) > 0
        if value == "*":
            atoms.append((value, None))
            return lambda values: True
        if re.match("https?://", value):
            atoms.append((value, None))
            return lambda values: value in values
        # a relative value matches verbatim or expanded with the prefix, so that
        # non-REFEDS claim values (acr = 1, amr = mfa, ...) are reachable too
        prefixed = prefix + value
        atoms.append((value, prefixed))
        return lambda values: value in values or prefixed in values

    return _Expression(expression, parse_expr(tokens), atoms)


class _OPAssurance:
    """Assurance policy of a single OP, with its tier expressions pre-parsed."""

    def __init__(self, op_authz: ConfigOPAuthZ):
        self._op_url = op_authz.op_url
        self._claims = op_authz.assurance_claims
        self._prefix = op_authz.assurance_prefix
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
        claims_found = set()
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
                claims_found.add(claim)
                logger.debug("Assurance claim '%s' from %s: %s", claim, source_name, sorted(found))
                values.update(found)

        if logger.isEnabledFor(logging.DEBUG):
            # An OP that renames or relocates a claim is otherwise invisible:
            # the configured claim simply stops being found and everyone quietly
            # drops to the fallback tier. Listing the claim NAMES each source
            # actually carries is what makes that diagnosable. Names only, never
            # values -- those are the user's data, and the ones we care about are
            # logged individually above.
            for source_name, src in sources:
                if src is None:
                    logger.debug("Assurance source %s: not present in this token", source_name)
                else:
                    logger.debug("Assurance source %s carries claims: %s", source_name, sorted(src))
            missing = [claim for claim in self._claims if claim not in claims_found]
            if missing:
                logger.debug(
                    "Assurance claims configured but found in no source: %s "
                    "(assurance_claims = %s for OP %s)",
                    missing,
                    self._claims,
                    self._op_url,
                )
                # The usual reason a claim is absent is that the token was never
                # issued with the scope that releases it. Different clients ask
                # for different scopes, so the very same user evaluates
                # differently depending on which client obtained the token --
                # which is otherwise only visible by diffing two runs.
                for source_name, src in sources:
                    if not src:
                        continue
                    scope = src.get("scope") or src.get("scp")
                    if scope:
                        logger.debug(
                            "Scopes on this token (%s): %s -- a claim that is missing "
                            "everywhere is usually a scope the token was not issued with",
                            source_name,
                            scope,
                        )
                        break
            logger.debug(
                "Assurance set for OP %s: %s",
                self._op_url,
                sorted(values) if values else "<empty>",
            )
        return values

    def evaluate(self, user_infos: UserInfos) -> Tuple[str, str]:
        """Return (shell tier, one-line reason) for the given user.

        The reason travels back to the AUDIT record, so the decision is
        explainable at any log level -- not only when DEBUG happens to be on.
        """
        values = self._assurance_set(user_infos)
        # State the inputs the expressions are resolved against. A stale prefix
        # -- an old package, or an explicit setting left in a config file that
        # upgrades do not touch -- makes every relative token expand to a URL no
        # provider asserts, which fails closed with nothing else to show for it.
        logger.debug(
            "Assurance policy for OP %s: assurance_prefix=%r, assurance_claims=%s, "
            "default_tier=%r, max_tier=%r",
            self._op_url,
            self._prefix,
            self._claims,
            self._default_tier,
            self._max_tier or "<none>",
        )
        tier = self._default_tier
        reason = ""
        for candidate in TIERS:
            req = self._tier_reqs.get(candidate)
            if req is None:
                continue
            matched = req(values)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Tier '%s' for OP %s: %s | expression: %s | %s",
                    candidate,
                    self._op_url,
                    "MATCH" if matched else "no match",
                    req.source if req.source else "<not configured>",
                    req.explain(values),
                )
            if matched:
                tier = candidate
                reason = f"matched assurance_based_shell_tier_{candidate}"
                break
        if not reason:
            reason = f"no tier expression matched, using default tier '{tier}'"
            logger.debug(
                "No tier expression matched for OP %s; falling back to '%s'", self._op_url, tier
            )
        capped = self._cap(tier, self._max_tier)
        if capped != tier:
            logger.debug(
                "Capping assurance tier %s to %s (assurance_based_shell_max_tier of %s)",
                tier,
                capped,
                self._op_url,
            )
            reason += f", then capped to '{capped}' by assurance_based_shell_max_tier"
        logger.debug("Evaluated assurance tier: %s (%s)", capped, reason)
        return capped, reason

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
        tier, reason = op_assurance.evaluate(user_infos)
        # this decides the user's login shell, so record it whatever the log
        # level -- including *why*, since a tier on its own does not say whether
        # the policy fired or the user just fell through to the default
        audit(
            logger,
            "Assurance tier '%s' for %s @ %s (%s)",
            tier,
            user_infos.subject,
            user_infos.issuer,
            reason,
        )
        return tier
