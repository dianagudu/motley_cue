import pytest

from flaat.user_infos import UserInfos
from flaat.access_tokens import AccessTokenInfo

from motley_cue.mapper.assurance import AssuranceEvaluator, parse_requirement
from motley_cue.mapper.config import Config, ConfigAssurance, ConfigOPAuthZ

from .configs import load_config, CONFIG_BASE

PREFIX = "https://refeds.org/assurance/"
MFA = "https://refeds.org/profile/mfa"
CAPPUCCINO = "https://refeds.org/assurance/profile/cappuccino"


def make_user_infos(user_info=None, at_body=None, introspection=None):
    """Build a (flaat) UserInfos with the given claim sources."""
    access_token_info = None
    if at_body is not None:
        access_token_info = AccessTokenInfo(
            complete_decode={"payload": at_body}, verification=None
        )
    return UserInfos(
        access_token_info=access_token_info,
        user_info=user_info,
        introspection_info=introspection,
    )


def default_evaluator():
    return AssuranceEvaluator(
        ConfigAssurance(
            tier_full=f"{MFA} & profile/cappuccino",
            tier_limited="profile/cappuccino",
            tier_restricted="*",
        )
    )


# ---------------------------------------------------------------------------
# parse_requirement grammar
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "expr,values,expected",
    [
        # relative claim expanded with prefix
        ("profile/cappuccino", {CAPPUCCINO}, True),
        ("profile/cappuccino", set(), False),
        # absolute URL kept as-is
        (MFA, {MFA}, True),
        (MFA, {CAPPUCCINO}, False),
        # conjunction / disjunction / precedence
        (f"{MFA} & profile/cappuccino", {MFA, CAPPUCCINO}, True),
        (f"{MFA} & profile/cappuccino", {CAPPUCCINO}, False),
        (f"{MFA} | profile/cappuccino", {CAPPUCCINO}, True),
        # '&' binds stronger than '|'
        (f"{MFA} & profile/cappuccino | profile/cappuccino", {CAPPUCCINO}, True),
        # parentheses
        (f"{MFA} & (profile/cappuccino | profile/espresso)", {MFA, CAPPUCCINO}, True),
        # special tokens
        ("+", {CAPPUCCINO}, True),
        ("+", set(), False),
        ("*", set(), True),
        # empty never matches
        ("", {CAPPUCCINO}, False),
        ("   ", {CAPPUCCINO}, False),
    ],
)
def test_parse_requirement(expr, values, expected):
    assert parse_requirement(expr, PREFIX)(values) is expected


@pytest.mark.parametrize("expr", ["a & (b", "a b )", "(a |"])
def test_parse_requirement_invalid(expr):
    with pytest.raises(ValueError):
        parse_requirement(expr, PREFIX)


# ---------------------------------------------------------------------------
# AssuranceEvaluator tier selection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "user_info,expected",
    [
        ({"eduperson_assurance": [CAPPUCCINO], "acr": MFA}, "full"),
        ({"eduperson_assurance": [CAPPUCCINO]}, "limited"),
        ({"eduperson_assurance": []}, "restricted"),
        ({}, "restricted"),
        # MFA but no profile -> neither full nor limited match -> fallback
        ({"acr": MFA}, "restricted"),
    ],
)
def test_evaluate_matrix(user_info, expected):
    assert default_evaluator().evaluate(make_user_infos(user_info)) == expected


def test_evaluate_acr_from_access_token_body():
    ui = make_user_infos({"eduperson_assurance": [CAPPUCCINO]}, at_body={"acr": MFA})
    assert default_evaluator().evaluate(ui) == "full"


def test_evaluate_acr_space_separated():
    ui = make_user_infos({"eduperson_assurance": [CAPPUCCINO], "acr": f"foo {MFA}"})
    assert default_evaluator().evaluate(ui) == "full"


def test_evaluate_acr_from_introspection():
    ui = make_user_infos(
        {"eduperson_assurance": [CAPPUCCINO]}, introspection={"acr": MFA}
    )
    assert default_evaluator().evaluate(ui) == "full"


@pytest.mark.parametrize(
    "max_tier,expected",
    [("", "full"), ("limited", "limited"), ("restricted", "restricted"), ("bogus", "full")],
)
def test_evaluate_per_op_cap(max_tier, expected):
    ui = make_user_infos({"eduperson_assurance": [CAPPUCCINO], "acr": MFA})
    op_authz = ConfigOPAuthZ(max_tier=max_tier)
    assert default_evaluator().evaluate(ui, op_authz) == expected


def test_cap_never_raises_tier():
    # a user who only qualifies for limited is not raised to full by max_tier=full
    ui = make_user_infos({"eduperson_assurance": [CAPPUCCINO]})
    assert default_evaluator().evaluate(ui, ConfigOPAuthZ(max_tier="full")) == "limited"


def test_default_tier_when_no_expression_matches():
    ev = AssuranceEvaluator(
        ConfigAssurance(tier_full="", tier_limited="", tier_restricted="", default_tier="limited")
    )
    assert ev.evaluate(make_user_infos({"eduperson_assurance": []})) == "limited"


# ---------------------------------------------------------------------------
# Config loading of the [assurance] section
# ---------------------------------------------------------------------------
def test_assurance_config_defaults():
    assurance = Config(load_config(CONFIG_BASE)).assurance
    assert assurance.prefix == "https://refeds.org/assurance/"
    assert assurance.claims == ["eduperson_assurance", "acr"]
    # feature is opt-in: unset tier expressions + default_tier "full"
    assert assurance.tier_full == ""
    assert assurance.tier_limited == ""
    assert assurance.tier_restricted == ""
    assert assurance.default_tier == "full"


def test_unconfigured_assurance_yields_full():
    """With no [assurance] configuration every user resolves to the full tier
    (backward compatible: feudalAdapter then uses its default shell)."""
    ev = AssuranceEvaluator(Config(load_config(CONFIG_BASE)).assurance)
    assert ev.evaluate(make_user_infos({})) == "full"
    assert ev.evaluate(make_user_infos({"eduperson_assurance": [CAPPUCCINO]})) == "full"


def test_assurance_config_loaded():
    config = load_config(
        f"""
{CONFIG_BASE}
[assurance]
prefix = https://example.org/assurance/
claims = [eduperson_assurance]
tier_full = {MFA} & profile/cappuccino
tier_limited = profile/cappuccino
tier_restricted = *
default_tier = restricted
"""
    )
    assurance = Config(config).assurance
    assert assurance.prefix == "https://example.org/assurance/"
    assert assurance.claims == ["eduperson_assurance"]
    assert assurance.tier_full == f"{MFA} & profile/cappuccino"
