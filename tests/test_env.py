import os
from dotenv import dotenv_values
import liboidcagent


environment = {
    **dotenv_values(".env"),
    **os.environ,
}


def env_var(name: str, mandatory: bool = True, default: str = "") -> str:
    if not mandatory:
        val = environment.get(name, default)
    else:
        val = environment.get(name, "")
        if val == "":  # pragma: no cover
            raise ValueError(f"Set '{name}' in environment or .env file")
    return val


def load_at(short_name: str) -> str:
    try:
        return liboidcagent.get_access_token(short_name)
    except liboidcagent.OidcAgentError as e:  # pragma: no cover
        raise Exception(
            f"Error acquiring access token for oidc agent account '{short_name}': {e}"
        ) from e


def get_at_from_env() -> str:
    for var in ["ACCESS_TOKEN", "OIDC", "OS_ACCESS_TOKEN", "OIDC_ACCESS_TOKEN"]:
        try:
            return env_var(var)
        except:
            continue
    try:
        return load_at(env_var("OIDC_AGENT_ACCOUNT"))
    except:
        raise ValueError("Set access token source in environment or .env file. Acceptable environment variables: ACCESS_TOKEN, OIDC, OS_ACCESS_TOKEN, OIDC_ACCESS_TOKEN (for access token); OIDC_AGENT_ACCOUNT (for oidc agent account)")



MC_TOKEN = get_at_from_env()
MC_SUB = env_var("MC_SUB")
MC_ISS = env_var("MC_ISS")
MC_VO = env_var("MC_VO")
MC_VO_CLAIM = env_var("MC_VO_CLAIM", mandatory=False, default="eduperson_entitlement")

