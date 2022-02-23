from io import StringIO
from configparser import ConfigParser

from .test_env import MC_SUB, MC_ISS, MC_VO, MC_VO_CLAIM


CONFIG_BASE = """
[mapper]
log_level = WARNING

[DEFAULT]
authorise_all = False
authorised_vos = []
vo_claim = eduperson_entitlement
vo_match = one
authorised_users = []
authorised_admins = []
authorise_admins_for_all_ops = False
"""

def load_config(s_config: str) -> ConfigParser:
    buf = StringIO(s_config)
    config = ConfigParser()
    config.read_file(buf)
    return config


CONFIG_NOT_SUPPORTED = load_config(f"""
{CONFIG_BASE}
""")

CONFIG_SUPPORTED_NOT_AUTHORISED = load_config(f"""
{CONFIG_BASE}
[authorisation.OP]
op_url = {MC_ISS}
""")

CONFIG_AUTHORISE_ALL = load_config(f"""
{CONFIG_BASE}
[authorisation.OP]
op_url = {MC_ISS}
authorise_all = True
""")

CONFIG_INDIVIDUAL = load_config(f"""
{CONFIG_BASE}
[authorisation.OP]
op_url = {MC_ISS}
authorised_users = [
        {MC_SUB}
    ]
""")

CONFIG_VO_BASED = load_config(f"""
{CONFIG_BASE}
[authorisation.OP]
op_url = {MC_ISS}
authorised_vos = [
        {MC_VO}
    ]
vo_claim = {MC_VO_CLAIM}
""")

CONFIG_ADMIN = load_config(f"""
{CONFIG_BASE}
[authorisation.OP]
op_url = {MC_ISS}
authorised_admins = [
        {MC_SUB}
    ]
""")

CONFIG_ADMIN_FOR_ALL = load_config(f"""
{CONFIG_BASE}
[authorisation.OP]
op_url = {MC_ISS}
authorised_admins = [
        {MC_SUB}
    ]
authorise_admins_for_all_ops = True
""")

CONFIG_DOC_ENABLED = load_config("""
[mapper]
enable_docs = True
""")

CONFIG_CUSTOM_DOC = load_config("""
[mapper]
enable_docs = True
docs_url = /api/v1/docs
""")

CONFIG_INVALID_CUSTOM_DOC = load_config("""
[mapper]
enable_docs = True
docs_url = docs
""")