import pytest

from .configs import (
    CONFIG_CUSTOM_DOC,
    CONFIG_DOC_ENABLED,
    CONFIG_INVALID,
    CONFIG_NOT_SUPPORTED,
    CONFIG_OTP_NOT_SUPPORTED,
    CONFIG_OTP_SUPPORTED,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://aai.egi.com/oidc",
        "http://aai.egi.com/oidc/",
        "https://aai.egi.com/oidc",
        "http://www.aai.egi.com/oidc",
        "aai.egi.com/oidc",
        "HTTP://AAI.EGI.COM/OIDC",
    ],
)
@pytest.mark.parametrize("canonical_form", ["aai.egi.com/oidc"])
def test_canonical_url(test_config, url, canonical_form):
    assert test_config.canonical_url(url) == canonical_form


@pytest.mark.parametrize(
    "list_str,real_list",
    [
        *[
            (ls, ["a", "b", "c"])
            for ls in [
                "[a,b,c]",
                "[a,b,c,]",
                '["a","b","c"]',
                "['a','b','c']",
                "[a, \n\tb, \n\tc]",
                "\n[a,b, c]\n",
            ]
        ],
        ("[\n\t  ]", []),
        ("[]", []),
        ("[,,,]", []),
        ("[[,]]", ["[", "]"]),
        ("[ [a,b,]]", ["[a", "b", "]"]),
    ],
)
def test_to_list(test_config, list_str, real_list):
    assert test_config.to_list(list_str) == real_list


@pytest.mark.parametrize("list_str", ["ddads[df,a,]", "][", ",[]"])
def test_to_list_invalid(test_config, test_internal_exception, list_str):
    with pytest.raises(test_internal_exception):
        test_config.to_list(list_str)


@pytest.mark.parametrize(
    "bool_str,real_bool",
    [
        *[(bs, True) for bs in ["true", "True", "TRUE", "tRue"]],
        *[(bs, False) for bs in ["false", "False", "FALSE", "fAlse"]],
    ],
)
def test_to_bool(test_config, bool_str, real_bool):
    assert test_config.to_bool(bool_str) == real_bool


@pytest.mark.parametrize("bool_str", ["something", "", "\n", " true", "false "])
def test_to_bool_invalid(test_config, test_internal_exception, bool_str):
    with pytest.raises(test_internal_exception):
        test_config.to_bool(bool_str)


def test_invalid_config(test_config):
    with pytest.raises(test_config.InternalException):
        test_config.Config(CONFIG_INVALID)


@pytest.mark.parametrize(
    "config_parser,docs_url",
    [
        (CONFIG_NOT_SUPPORTED, None),
        (CONFIG_DOC_ENABLED, "/docs"),
        (CONFIG_CUSTOM_DOC, "/api/v1/docs"),
    ],
)
def test_docs_url(test_config, config_parser, docs_url):
    assert test_config.Config(config_parser).docs_url == docs_url


@pytest.mark.parametrize(
    "config_parser,use_otp",
    [
        (CONFIG_NOT_SUPPORTED, False),
        (CONFIG_OTP_NOT_SUPPORTED, False),
        (CONFIG_OTP_SUPPORTED, True),
    ],
)
def test_otp(test_config, config_parser, use_otp):
    otp_config = test_config.Config(config_parser).otp
    assert otp_config.use_otp == use_otp
    assert otp_config.backend == "sqlite"
    assert otp_config.db_location == "/run/motley_cue/tokenmap.db"
    assert otp_config.keyfile == "/run/motley_cue/motley_cue.key"
