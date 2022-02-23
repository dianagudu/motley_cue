import pytest


@pytest.mark.parametrize("url", [
    "http://aai.egi.com/oidc",
    "http://aai.egi.com/oidc/",
    "https://aai.egi.com/oidc",
    "http://www.aai.egi.com/oidc",
    "aai.egi.com/oidc",
    "HTTP://AAI.EGI.COM/OIDC",
])
@pytest.mark.parametrize("canonical_form", ["aai.egi.com/oidc"])
def test_canonical_url(test_config, url, canonical_form):
    assert test_config.canonical_url(url) == canonical_form


@pytest.mark.parametrize("list_str,real_list", [
    *[(ls, ["a", "b", "c"]) for ls in [
        "[a,b,c]",
        "[a,b,c,]",
        "[\"a\",\"b\",\"c\"]",
        "['a','b','c']",
        "[a, \n\tb, \n\tc]",
        "\n[a,b, c]\n",
    ]],
    ("[\n\t  ]", []),
    ("[]", []),
    ("[,,,]", []),
    ("[[,]]", ["[", "]"]),
    ("[ [a,b,]]", ["[a", "b", "]"])
])
def test_to_list(test_config, list_str, real_list):
    assert test_config.to_list(list_str) == real_list


@pytest.mark.parametrize("list_str", [
    "ddads[df,a,]",
    "][",
    ",[]"
])
def test_to_list_invalid(test_config, test_internal_exception, list_str):
    with pytest.raises(test_internal_exception):
        test_config.to_list(list_str)


@pytest.mark.parametrize("bool_str,real_bool", [
    *[(bs, True) for bs in ["true", "True", "TRUE", "tRue"]],
    *[(bs, False) for bs in ["false", "False", "FALSE", "fAlse"]],
])
def test_to_bool(test_config, bool_str, real_bool):
    assert test_config.to_bool(bool_str) == real_bool


@pytest.mark.parametrize("bool_str", ["something", "", "\n", " true", "false "])
def test_to_bool_invalid(test_config, test_internal_exception, bool_str):
    with pytest.raises(test_internal_exception):
        test_config.to_bool(bool_str)