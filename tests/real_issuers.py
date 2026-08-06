"""Merged userinfos (userinfo + access token body + introspection) as really
returned by various OPs, for assurance evaluation tests.

The JSON below is verbatim real-world data; only structural defects that made
it unparseable were repaired. Note the raw strings: `ssh_public_key` contains a
literal backslash-n, which a normal triple-quoted string would turn into an
actual newline and thus into invalid JSON.

Each name is exported as a parsed `dict`, ready to hand to `make_user_infos`.
"""

import json

# IRIS asserts MFA via `acr`, but only IAP/low assurance -- no REFEDS profile.
IRIS_JSON = r"""
{
    "acr": "https://refeds.org/profile/mfa",
    "client_id": "253f573c-3cbb-4099-82d3-214600c15f66",
    "eduperson_assurance": [
        "https://refeds.org/assurance/IAP/low",
        "https://refeds.org/assurance"
    ],
    "eduperson_scoped_affiliation": "member@iam.example",
    "email": "marcus.hardt@kit.edu",
    "exp": 1786005535,
    "iat": 1786001935,
    "iss": "https://iris-iam.stfc.ac.uk/",
    "jti": "9e4b9d66-b811-46cb-914e-31346edf93b5",
    "nbf": 1786001875,
    "preferred_username": "lo0018@kit.edu",
    "sub": "e667eaef-0b79-4220-b4e1-353556da028c",
    "email_verified": true,
    "aarc_ver": "https://aarc-community.org/attribute/profile/version/1.0",
    "family_name": "Hardt",
    "given_name": "Marcus",
    "name": "Marcus Hardt",
    "voperson_id": "e667eaef-0b79-4220-b4e1-353556da028c@iam.example"
}
"""

# KIT asserts no REFEDS assurance at all, and an `acr` of "0".
KIT_JSON = r"""
{
    "acr": "0",
    "auth_time": 1784104692,
    "azp": "7b3b85df-1965-41b9-b4e2-476f0eb0d5df",
    "eduperson_principal_name": "lo0018@kit.edu",
    "eduperson_scoped_affiliation": [
        "member@kit.edu",
        "faculty@kit.edu",
        "employee@kit.edu"
    ],
    "email": "marcus.hardt@kit.edu",
    "exp": 1786004546,
    "iat": 1786004246,
    "iss": "https://oidc.scc.kit.edu/auth/realms/kit",
    "jti": "ofrtrt:d6b26dcb-81b1-730a-7128-f45ec8fb92b0",
    "preferred_username": "lo0018",
    "scope": "openid entitlements profile microprofile-jwt email address memberOf orcid phone base",
    "sid": "ZwIKAa4v-bfIk88pqeSUQB-d",
    "sub": "4cbcd471-1f51-4e54-97b8-2dd5177e25ec",
    "typ": "Bearer",
    "upn": "lo0018@kit.edu",
    "display_name": "Hardt, Marcus (SCC)",
    "eduperson_entitlement": [],
    "eduperson_orcid": "https://orcid.org/0000-0001-9149-244X",
    "family_name": "Hardt",
    "given_name": "Marcus",
    "name": "Marcus Hardt",
    "ou": "SCC",
    "schac_personal_title": "Dr."
}
"""

# Helmholtz asserts both MFA (via `acr`) and the REFEDS cappuccino profile.
HELMHOLTZ_JSON = r"""
{
    "acr": "https://refeds.org/profile/mfa",
    "aud": "public-oidc-agent",
    "auth_time": 1784269312,
    "client_id": "public-oidc-agent",
    "display_name": "Marcus Hardt",
    "eduperson_assurance": [
        "https://refeds.org/assurance",
        "https://refeds.org/assurance/ID/unique",
        "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
        "https://refeds.org/assurance/ATP/ePA-1d",
        "https://refeds.org/assurance/ATP/ePA-1m",
        "https://refeds.org/assurance/IAP/local-enterprise",
        "https://refeds.org/assurance/IAP/low",
        "https://refeds.org/assurance/IAP/medium",
        "https://refeds.org/assurance/profile/cappuccino",
        "https://aarc-project.eu/policy/authn-assurance/assam"
    ],
    "eduperson_principal_name": "lo0018@kit.edu",
    "eduperson_scoped_affiliation": [
        "employee@login.helmholtz.de",
        "member@login.helmholtz.de"
    ],
    "eduperson_unique_id": "6c611e2a2c1c487f9948c058a36c8f0e@login.helmholtz.de",
    "email": "marcus.hardt@kit.edu",
    "email_verified": true,
    "entitlements": [
        "urn:mace:dir:entitlement:common-lib-terms",
        "http://bwidm.de/entitlement/bwLSDF-SyncShare",
        "urn:geant:helmholtz.de:group:KIT#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:Helmholtz-member#login.helmholtz.de",
        "urn:geant:h-df.de:group:m-team:feudal-developers#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:Arbeitskreise#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:HIFIS:Associates#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:Arbeitskreise:AG IT Services#login.helmholtz.de",
        "urn:geant:h-df.de:group:m-team#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:Helmholtz-all#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:IAM4NFDI#login.helmholtz.de",
        "urn:geant:helmholtz.de:group:HIFIS#login.helmholtz.de"
    ],
    "exp": 1786005937,
    "family_name": "Hardt",
    "given_name": "Marcus",
    "iat": 1786001937,
    "iss": "https://login.helmholtz.de/oauth2",
    "jti": "7dac5013-2a9a-4d8f-9e5c-4cb5dbe78696",
    "name": "Marcus Hardt",
    "org_domain": "kit.edu",
    "preferred_username": "marcus",
    "scope": "entitlements voperson_external_affiliation sys:scim:read_self_group sys:scim:read_memberships credentials openid profile display_name eduperson_entitlement token-exchange eduperson_principal_name acr voperson_id org_domain eduperson_scoped_affiliation eduperson_unique_id sys:scim:read_profile eduperson_assurance sn email single-logout",
    "sn": "Hardt",
    "ssh_public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAqA5FW6m3FbFhCOsRQBxKMRki5qJxoNhZdaeLXg6ym/ marcus@test2022\n",
    "sub": "6c611e2a-2c1c-487f-9948-c058a36c8f0e",
    "voperson_external_affiliation": [
        "employee@kit.edu",
        "faculty@kit.edu",
        "member@kit.edu"
    ],
    "voperson_id": "6c611e2a2c1c487f9948c058a36c8f0e@login.helmholtz.de"
}
"""

# EGI asserts the REFEDS cappuccino profile, but no MFA.
EGI_JSON = r"""
{
    "auth_time": 1785487892,
    "azp": "oidc-agent",
    "eduperson_assurance": [
        "https://refeds.org/assurance/profile/cappuccino",
        "https://refeds.org/assurance/IAP/medium",
        "https://refeds.org/assurance/IAP/low",
        "https://refeds.org/assurance/IAP/local-enterprise",
        "https://refeds.org/assurance/ATP/ePA-1m",
        "https://refeds.org/assurance/ATP/ePA-1d",
        "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
        "https://refeds.org/assurance/ID/unique",
        "https://refeds.org/assurance"
    ],
    "exp": 1786005539,
    "iat": 1786001939,
    "iss": "https://aai.egi.eu/auth/realms/egi",
    "jti": "1c77bac3-0c78-4eb0-9d8b-1a4111ad1cd4",
    "scope": "openid entitlements voperson_id profile email",
    "session_state": "090bb724-e628-4c50-858f-4530dadb7377",
    "sid": "090bb724-e628-4c50-858f-4530dadb7377",
    "sub": "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu",
    "typ": "Bearer",
    "email": "hardt@kit.edu",
    "email_verified": true,
    "entitlements": [
        "urn:mace:egi.eu:group:o3as.data.kit.edu:role=member#aai.egi.eu",
        "urn:mace:egi.eu:res:ggus.eu",
        "urn:mace:egi.eu:res:gocdb#aai.egi.eu",
        "urn:mace:egi.eu:group:o3as.data.kit.edu:role=vm_operator#aai.egi.eu",
        "urn:mace:egi.eu:group:mteam.data.kit.edu:perfmon.m.d.k.e:role=member#aai.egi.eu",
        "urn:mace:egi.eu:res:rcauth#aai.egi.eu"
    ],
    "family_name": "Hardt",
    "given_name": "Marcus",
    "name": "Marcus Hardt",
    "preferred_username": "mhardt",
    "voperson_id": "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu",
    "voperson_verified_email": [
        "hardt@kit.edu"
    ]
}
"""

IRIS = json.loads(IRIS_JSON)
KIT = json.loads(KIT_JSON)
HELMHOLTZ = json.loads(HELMHOLTZ_JSON)
EGI = json.loads(EGI_JSON)

# issuer of each, for configuring an evaluator that actually matches them
ISSUERS = {
    "IRIS": IRIS["iss"],
    "KIT": KIT["iss"],
    "HELMHOLTZ": HELMHOLTZ["iss"],
    "EGI": EGI["iss"],
}
