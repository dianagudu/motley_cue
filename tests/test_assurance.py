import pytest

from flaat.user_infos import UserInfos
from flaat.access_tokens import AccessTokenInfo

from motley_cue.mapper.assurance import AssuranceEvaluator, parse_requirement
from motley_cue.mapper.config import Config, ConfigAuthorisation, ConfigOPAuthZ, canonical_url
from motley_cue.mapper.exceptions import InternalException

from .real_issuers import KIT, IRIS, HELMHOLTZ, EGI, ISSUERS

from .configs import load_config, CONFIG_BASE
from .utils import MOCK_ISS

PREFIX = "https://refeds.org/assurance/"
MFA = "https://refeds.org/profile/mfa"
CAPPUCCINO = "https://refeds.org/assurance/profile/cappuccino"

OTHER_ISS = "https://other.issuer/oidc"


def make_user_infos(user_info=None, at_body=None, introspection=None, iss=MOCK_ISS):
    """Build a (flaat) UserInfos with the given claim sources."""
    access_token_info = None
    if at_body is not None:
        access_token_info = AccessTokenInfo(complete_decode={"payload": at_body}, verification=None)
    user_info = dict(user_info or {})
    # NB: this *overrides* any `iss` the claims already carry. Real-world
    # userinfos (see real_issuers.py) come with their own issuer; letting it
    # through would make the evaluator miss the OP configured by
    # `evaluator_for` and silently fall back to the built-in defaults, i.e.
    # "full" -- so every test would pass for the wrong reason.
    user_info["iss"] = iss
    return UserInfos(
        access_token_info=access_token_info,
        user_info=user_info,
        introspection_info=introspection,
    )


def evaluator_for(**op_kwargs) -> AssuranceEvaluator:
    """An evaluator with a single OP at MOCK_ISS configured as given."""
    return AssuranceEvaluator(
        ConfigAuthorisation({MOCK_ISS.replace("https://", ""): ConfigOPAuthZ(**op_kwargs)})
    )


def default_evaluator() -> AssuranceEvaluator:
    return evaluator_for(
        op_url=MOCK_ISS,
        assurance_based_shell_tier_full=f"{MFA} & profile/cappuccino",
        assurance_based_shell_tier_limited="profile/cappuccino",
        assurance_based_shell_tier_restricted="*",
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
        # a relative token also matches a raw (unprefixed) claim value, so that
        # non-REFEDS values such as an acr of "1" or an amr of "mfa" are reachable
        ("1", {"1"}, True),
        ("mfa", {"mfa"}, True),
        ("1", {f"{PREFIX}1"}, True),
        ("1", {"2"}, False),
        # an absolute token is NOT matched by a bare value of the same name
        (MFA, {"mfa"}, False),
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


def test_invalid_expression_fails_at_startup():
    """A malformed tier expression is reported as an InternalException naming
    the OP and the expression, rather than a bare ValueError from the parser."""
    with pytest.raises(InternalException) as excinfo:
        evaluator_for(op_url=MOCK_ISS, assurance_based_shell_tier_full="a & (b")
    assert MOCK_ISS in str(excinfo.value)
    assert "assurance_based_shell_tier_full" in str(excinfo.value)


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
        # real-world merged userinfos, against the policy in default_evaluator():
        #   full      = <MFA> & profile/cappuccino
        #   limited   = profile/cappuccino
        #   restricted= *
        # IRIS asserts MFA via acr, but only IAP/low -- no cappuccino profile,
        # so `full` cannot match and neither can `limited`.
        (IRIS, "restricted"),
        # Helmholtz asserts both MFA and cappuccino.
        (HELMHOLTZ, "full"),
        # KIT asserts no REFEDS attributes at all (acr = "0").
        (KIT, "restricted"),
        # EGI asserts cappuccino but no MFA.
        (EGI, "limited"),
    ],
)
def test_evaluate_matrix(user_info, expected):
    assert default_evaluator().evaluate(make_user_infos(user_info)) == expected


def test_evaluate_acr_space_separated():
    ui = make_user_infos({"eduperson_assurance": [CAPPUCCINO], "acr": f"foo {MFA}"})
    assert default_evaluator().evaluate(ui) == "full"


def test_evaluate_raw_acr_value():
    """An OP that signals its assurance level as a bare acr value (not a REFEDS
    URL) can be matched by writing that value directly."""
    ev = evaluator_for(
        op_url=MOCK_ISS,
        assurance_based_shell_tier_full="2",
        assurance_based_shell_tier_restricted="*",
    )
    assert ev.evaluate(make_user_infos({"acr": "2"})) == "full"
    assert ev.evaluate(make_user_infos({"acr": "1"})) == "restricted"


# ---------------------------------------------------------------------------
# Claim collection: the union of ALL sources decides, not the first one
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "source",
    ["user_info", "access_token_info.body", "introspection_info"],
)
def test_claims_collected_from_every_source(source):
    """A tier-deciding claim is picked up no matter which of the three token
    sources carries it."""
    claims = {"eduperson_assurance": [CAPPUCCINO], "acr": MFA}
    kwargs = {
        "user_info": claims if source == "user_info" else None,
        "at_body": claims if source == "access_token_info.body" else None,
        "introspection": claims if source == "introspection_info" else None,
    }
    assert default_evaluator().evaluate(make_user_infos(**kwargs)) == "full"


@pytest.mark.parametrize(
    "at_body,introspection",
    [
        ({"acr": MFA}, None),
        (None, {"acr": MFA}),
    ],
)
def test_claims_are_unioned_across_sources(at_body, introspection):
    """`full` needs cappuccino AND mfa; they arrive from different sources, so
    only the union of all sources can satisfy it. flaat's own UserInfos.get()
    is first-match-wins and would not see the second value."""
    ui = make_user_infos(
        {"eduperson_assurance": [CAPPUCCINO]},
        at_body=at_body,
        introspection=introspection,
    )
    assert default_evaluator().evaluate(ui) == "full"


def test_same_claim_in_several_sources_is_unioned():
    """The same claim name in two sources contributes both sets of values,
    rather than the first source shadowing the second."""
    ui = make_user_infos(
        {"eduperson_assurance": [CAPPUCCINO]},
        at_body={"eduperson_assurance": [MFA]},
    )
    assert default_evaluator().evaluate(ui) == "full"


# ---------------------------------------------------------------------------
# Per-OP policy: [DEFAULT] inheritance and overrides
# ---------------------------------------------------------------------------
ASSURANCE_DEFAULTS = f"""
assurance_based_shell_tier_full = {MFA} & profile/cappuccino
assurance_based_shell_tier_limited = profile/cappuccino
assurance_based_shell_tier_restricted = *
"""


def config_with_two_ops(op2_extra: str = "") -> Config:
    return Config(load_config(f"""
{CONFIG_BASE}
{ASSURANCE_DEFAULTS}

[authorisation.op1]
op_url = {MOCK_ISS}

[authorisation.op2]
op_url = {OTHER_ISS}
{op2_extra}
"""))


def test_default_section_applies_to_every_op():
    """An OP that sets no assurance option at all inherits the [DEFAULT] one."""
    config = config_with_two_ops()
    for op_authz in config.authorisation.all_op_authz.values():
        assert op_authz.assurance_based_shell_tier_full == f"{MFA} & profile/cappuccino"

    ev = AssuranceEvaluator(config.authorisation)
    claims = {"eduperson_assurance": [CAPPUCCINO], "acr": MFA}
    assert ev.evaluate(make_user_infos(claims, iss=MOCK_ISS)) == "full"
    assert ev.evaluate(make_user_infos(claims, iss=OTHER_ISS)) == "full"


def test_op_overrides_default_expression():
    """The same claims give different tiers for two OPs, because one overrides
    the inherited expression."""
    config = config_with_two_ops("assurance_based_shell_tier_full = profile/espresso")
    ev = AssuranceEvaluator(config.authorisation)
    claims = {"eduperson_assurance": [CAPPUCCINO], "acr": MFA}
    assert ev.evaluate(make_user_infos(claims, iss=MOCK_ISS)) == "full"
    assert ev.evaluate(make_user_infos(claims, iss=OTHER_ISS)) == "limited"


def test_op_max_tier_caps_inherited_policy():
    config = config_with_two_ops("assurance_based_shell_max_tier = limited")
    ev = AssuranceEvaluator(config.authorisation)
    claims = {"eduperson_assurance": [CAPPUCCINO], "acr": MFA}
    assert ev.evaluate(make_user_infos(claims, iss=MOCK_ISS)) == "full"
    assert ev.evaluate(make_user_infos(claims, iss=OTHER_ISS)) == "limited"


def test_op_overrides_claims_and_prefix():
    config = config_with_two_ops(
        "assurance_claims = [eduperson_assurance]\n"
        "assurance_prefix = https://example.org/assurance/"
    )
    op2 = config.authorisation.all_op_authz["other.issuer/oidc"]
    assert op2.assurance_claims == ["eduperson_assurance"]
    assert op2.assurance_prefix == "https://example.org/assurance/"

    ev = AssuranceEvaluator(config.authorisation)
    # acr is no longer collected for op2, so MFA is invisible there
    claims = {"eduperson_assurance": [CAPPUCCINO], "acr": MFA}
    assert ev.evaluate(make_user_infos(claims, iss=OTHER_ISS)) == "restricted"


def test_unknown_op_falls_back_to_configured_defaults():
    """A token from an OP without its own section (not authorised anyway) still
    evaluates, and it uses the operator's [DEFAULT] policy -- whose catch-all
    `assurance_based_shell_tier_restricted = *` matches -> restricted."""
    ev = AssuranceEvaluator(config_with_two_ops().authorisation)
    assert ev.evaluate(make_user_infos({}, iss="https://unknown.issuer/")) == "restricted"


def test_unknown_op_without_configured_defaults_uses_builtin_defaults():
    """With no assurance policy configured at all, the feature stays opt-out:
    an unknown OP resolves to the built-in default tier."""
    ev = AssuranceEvaluator(Config(load_config(CONFIG_BASE)).authorisation)
    assert ev.evaluate(make_user_infos({}, iss="https://unknown.issuer/")) == "full"


def test_unknown_op_respects_default_max_tier():
    """A cap set in [DEFAULT] also applies to an OP without its own section."""
    config = Config(load_config(f"{CONFIG_BASE}assurance_based_shell_max_tier = limited\n"))
    ev = AssuranceEvaluator(config.authorisation)
    assert ev.evaluate(make_user_infos({}, iss="https://unknown.issuer/")) == "limited"


@pytest.mark.parametrize(
    "max_tier,expected",
    [("", "full"), ("limited", "limited"), ("restricted", "restricted")],
)
def test_max_tier_cap(max_tier, expected):
    ev = evaluator_for(
        op_url=MOCK_ISS,
        assurance_based_shell_tier_full=f"{MFA} & profile/cappuccino",
        assurance_based_shell_tier_limited="profile/cappuccino",
        assurance_based_shell_tier_restricted="*",
        assurance_based_shell_max_tier=max_tier,
    )
    ui = make_user_infos({"eduperson_assurance": [CAPPUCCINO], "acr": MFA})
    assert ev.evaluate(ui) == expected


# ---------------------------------------------------------------------------
# Real issuers, evaluated under their own issuer URL (as in production)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name,claims,expected",
    [
        ("IRIS", IRIS, "restricted"),
        ("KIT", KIT, "restricted"),
        ("HELMHOLTZ", HELMHOLTZ, "full"),
        ("EGI", EGI, "limited"),
    ],
)
def test_real_issuer_under_its_own_issuer_url(name, claims, expected):
    """Same policy, but each OP configured under its real issuer URL, so the
    per-OP lookup hits instead of falling back. This is the production path."""
    op_url = ISSUERS[name]
    ev = AssuranceEvaluator(
        ConfigAuthorisation(
            {
                canonical_url(op_url): ConfigOPAuthZ(
                    op_url=op_url,
                    assurance_based_shell_tier_full=f"{MFA} & profile/cappuccino",
                    assurance_based_shell_tier_limited="profile/cappuccino",
                    assurance_based_shell_tier_restricted="*",
                )
            }
        )
    )
    assert ev.evaluate(make_user_infos(claims, iss=op_url)) == expected


def test_refeds_mfa_is_not_under_the_assurance_prefix():
    """`https://refeds.org/profile/mfa` does NOT live under the default
    assurance_prefix, so the relative token `profile/mfa` can never match it --
    an expression written that way silently never fires. It must either be
    given as an absolute URL, or the prefix must be widened.
    """
    relative = dict(
        op_url=MOCK_ISS,
        assurance_based_shell_tier_limited="profile/mfa",
        assurance_based_shell_tier_restricted="*",
    )
    # with the default prefix (.../assurance/) the relative token cannot match
    assert evaluator_for(**relative).evaluate(make_user_infos(IRIS)) == "restricted"
    # widening the prefix to the refeds root makes it match
    assert (
        evaluator_for(assurance_prefix="https://refeds.org/", **relative).evaluate(
            make_user_infos(IRIS)
        )
        == "limited"
    )
    # the absolute URL always works, whatever the prefix
    assert (
        evaluator_for(
            op_url=MOCK_ISS,
            assurance_based_shell_tier_limited=MFA,
            assurance_based_shell_tier_restricted="*",
        ).evaluate(make_user_infos(IRIS))
        == "limited"
    )


@pytest.mark.parametrize("bad", ["bogus", "Limited", "LIMITED", "restrictd", "none"])
def test_invalid_max_tier_fails_at_startup(bad):
    """An unrecognised max_tier must not be ignored: doing so drops the cap and
    hands the user MORE privilege than configured."""
    with pytest.raises(InternalException) as excinfo:
        evaluator_for(op_url=MOCK_ISS, assurance_based_shell_max_tier=bad)
    assert "assurance_based_shell_max_tier" in str(excinfo.value)


@pytest.mark.parametrize("bad", ["resticted", "Restricted", "nologin", "full "])
def test_invalid_default_tier_fails_at_startup(bad):
    """An unrecognised default_tier used to be passed to feudalAdapter verbatim,
    which maps any unknown tier to its default (full) shell."""
    with pytest.raises(InternalException) as excinfo:
        evaluator_for(op_url=MOCK_ISS, assurance_based_shell_default_tier=bad)
    assert "assurance_based_shell_default_tier" in str(excinfo.value)


def test_invalid_tier_in_default_section_fails_at_startup():
    """The same validation applies to the [DEFAULT] section."""
    with pytest.raises(InternalException):
        AssuranceEvaluator(
            Config(
                load_config(f"{CONFIG_BASE}assurance_based_shell_max_tier = bogus\n")
            ).authorisation
        )


def test_default_tier_is_least_privileged_once_a_policy_exists():
    """An OP with a policy whose expressions never match must NOT fall through
    to "full". This is the MFA-prefix trap: `profile/mfa` expands to a URL no
    provider asserts, so nothing matches."""
    ev = evaluator_for(
        op_url=MOCK_ISS,
        # can never match: refeds MFA is not under the assurance prefix
        assurance_based_shell_tier_full="profile/mfa",
    )
    assert ev.evaluate(make_user_infos(IRIS)) == "restricted"


def test_explicit_default_tier_still_wins_over_the_automatic_one():
    """An operator who deliberately wants fail-open can still say so."""
    ev = evaluator_for(
        op_url=MOCK_ISS,
        assurance_based_shell_tier_full="profile/mfa",
        assurance_based_shell_default_tier="full",
    )
    assert ev.evaluate(make_user_infos(IRIS)) == "full"


def test_policy_on_one_op_does_not_affect_another():
    """Configuring assurance for a single OP must leave the others alone."""
    config = Config(load_config(f"""
{CONFIG_BASE}
[authorisation.op1]
op_url = {MOCK_ISS}
assurance_based_shell_tier_full = {MFA} & profile/cappuccino

[authorisation.op2]
op_url = {OTHER_ISS}
"""))
    ev = AssuranceEvaluator(config.authorisation)
    # op1 has a policy: a user not matching it is NOT given a full shell
    assert ev.evaluate(make_user_infos(IRIS, iss=MOCK_ISS)) == "restricted"
    # op2 has none, so it is untouched -- feature stays off for it
    assert ev.evaluate(make_user_infos(IRIS, iss=OTHER_ISS)) == "full"
    assert ev.evaluate(make_user_infos(KIT, iss=OTHER_ISS)) == "full"


def test_default_section_policy_applies_to_every_op_including_unknown():
    """Anything set in [DEFAULT] applies to all OPs, configured or not."""
    config = Config(load_config(f"""
{CONFIG_BASE}
assurance_based_shell_tier_full = {MFA} & profile/cappuccino

[authorisation.op1]
op_url = {MOCK_ISS}

[authorisation.op2]
op_url = {OTHER_ISS}
"""))
    ev = AssuranceEvaluator(config.authorisation)
    for iss in (MOCK_ISS, OTHER_ISS, "https://unknown.issuer/"):
        assert ev.evaluate(make_user_infos(HELMHOLTZ, iss=iss)) == "full"
        assert ev.evaluate(make_user_infos(KIT, iss=iss)) == "restricted"


def test_cap_never_raises_tier():
    # a user who only qualifies for limited is not raised to full by max_tier=full
    ev = evaluator_for(
        op_url=MOCK_ISS,
        assurance_based_shell_tier_full=f"{MFA} & profile/cappuccino",
        assurance_based_shell_tier_limited="profile/cappuccino",
        assurance_based_shell_tier_restricted="*",
        assurance_based_shell_max_tier="full",
    )
    assert ev.evaluate(make_user_infos({"eduperson_assurance": [CAPPUCCINO]})) == "limited"


def test_default_tier_when_no_expression_matches():
    ev = evaluator_for(op_url=MOCK_ISS, assurance_based_shell_default_tier="limited")
    assert ev.evaluate(make_user_infos({"eduperson_assurance": []})) == "limited"


# ---------------------------------------------------------------------------
# Config defaults: the feature is opt-in
# ---------------------------------------------------------------------------
def test_assurance_config_defaults():
    op_authz = ConfigOPAuthZ()
    assert op_authz.assurance_prefix == "https://refeds.org/assurance/"
    assert op_authz.assurance_claims == ["assurance", "eduperson_assurance", "acr"]
    # feature is opt-in: no tier expressions, and the default tier is left
    # unset ("") so that it can be resolved per OP -- see
    # test_default_tier_is_least_privileged_once_a_policy_exists
    assert op_authz.assurance_based_shell_tier_full == ""
    assert op_authz.assurance_based_shell_tier_limited == ""
    assert op_authz.assurance_based_shell_tier_restricted == ""
    assert op_authz.assurance_based_shell_default_tier == ""
    assert op_authz.assurance_based_shell_max_tier == ""


def test_unconfigured_assurance_yields_full():
    """With no assurance configuration every user resolves to the full tier
    (backward compatible: feudalAdapter then uses its default shell)."""
    config = Config(load_config(f"""
{CONFIG_BASE}
[authorisation.op1]
op_url = {MOCK_ISS}
"""))
    ev = AssuranceEvaluator(config.authorisation)
    assert ev.evaluate(make_user_infos({})) == "full"
    assert ev.evaluate(make_user_infos({"eduperson_assurance": [CAPPUCCINO]})) == "full"


def test_assurance_config_loaded():
    config = Config(load_config(f"""
{CONFIG_BASE}
[authorisation.op1]
op_url = {MOCK_ISS}
assurance_prefix = https://example.org/assurance/
assurance_claims = [eduperson_assurance]
assurance_based_shell_tier_full = {MFA} & profile/cappuccino
assurance_based_shell_tier_limited = {MFA} | profile/cappuccino 
assurance_based_shell_tier_restricted = *
assurance_based_shell_default_tier = restricted
assurance_based_shell_max_tier = limited
"""))
    op_authz = config.authorisation.all_op_authz["mock.issuer/oidc"]
    assert op_authz.assurance_prefix == "https://example.org/assurance/"
    assert op_authz.assurance_claims == ["eduperson_assurance"]
    assert op_authz.assurance_based_shell_tier_full == f"{MFA} & profile/cappuccino"
    assert op_authz.assurance_based_shell_tier_limited == f"{MFA} | profile/cappuccino"
    assert op_authz.assurance_based_shell_tier_restricted == "*"
    assert op_authz.assurance_based_shell_default_tier == "restricted"
    assert op_authz.assurance_based_shell_max_tier == "limited"
