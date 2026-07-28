"""Assurance evaluation: map a user's assurance/MFA claims to a shell tier.

This logic was formerly part of feudalAdapter (a single global
``assurance.require`` expression gating deployment). It now lives in motley_cue,
which has the per-OP context and the full token (userinfo, access-token body,
introspection). Instead of rejecting, the evaluation classifies each user into a
shell *tier* that is passed to feudalAdapter, which maps it to a login shell.
"""

import logging
import re
from typing import Callable, Optional, Set

from flaat.user_infos import UserInfos

from motley_cue.mapper.config import ConfigAssurance, ConfigOPAuthZ

logger = logging.getLogger(__name__)

# Tiers in priority order, highest privilege first.
TIERS = ["full", "limited", "restricted"]

# Tokeniser for the assurance boolean grammar.
_TOKEN_RE = re.compile(r"&|\||\(|\)|[^\s()&|]+")


def parse_requirement(expression: str, prefix: str) -> Callable[[Set[str]], bool]:
    """Parse a boolean assurance expression into a predicate over a set of claim values.

    Grammar: ``E -> E "&" E | E "|" E | "(" E ")" | string``, where ``&`` binds
    stronger than ``|``. A string is an absolute claim value (if it starts with
    ``http[s]://``) or is interpreted relative to ``prefix``. ``"+"`` matches if
    the user has any claim at all; ``"*"`` always matches. An empty expression
    never matches.
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
        value = value if re.match("https?://", value) else prefix + value
        return lambda values: value in values

    return parse_expr(tokens)


class AssuranceEvaluator:
    """Classifies a user into a shell tier based on their assurance claims."""

    def __init__(self, config: ConfigAssurance):
        self._claims = config.claims
        self._default_tier = config.default_tier
        self._tier_reqs = {
            "full": parse_requirement(config.tier_full, config.prefix),
            "limited": parse_requirement(config.tier_limited, config.prefix),
            "restricted": parse_requirement(config.tier_restricted, config.prefix),
        }

    def _assurance_set(self, user_infos: UserInfos) -> Set[str]:
        """Collect the union of all configured claim values from every available
        token source (userinfo, access-token body, introspection)."""
        values: Set[str] = set()
        access_token_info = getattr(user_infos, "access_token_info", None)
        sources = [
            getattr(user_infos, "user_info", None),
            getattr(access_token_info, "body", None),
            getattr(user_infos, "introspection_info", None),
        ]
        for claim in self._claims:
            for src in sources:
                if not src:
                    continue
                val = src.get(claim)
                if val is None:
                    continue
                if isinstance(val, str):
                    # a claim like `acr` may be a single value or a
                    # space-separated list of class references
                    values.add(val)
                    values.update(val.split())
                elif isinstance(val, (list, tuple, set)):
                    values.update(str(v) for v in val)
                else:
                    values.add(str(val))
        return values

    def evaluate(self, user_infos: UserInfos, op_authz: Optional[ConfigOPAuthZ] = None) -> str:
        """Return the shell tier for the given user, optionally capped per-OP."""
        values = self._assurance_set(user_infos)
        tier = self._default_tier
        for candidate in TIERS:
            req = self._tier_reqs.get(candidate)
            if req is not None and req(values):
                tier = candidate
                break
        max_tier = getattr(op_authz, "max_tier", "") if op_authz is not None else ""
        capped = self._cap(tier, max_tier)
        if capped != tier:
            logger.debug("Capping assurance tier %s to %s (per-OP max_tier)", tier, capped)
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
