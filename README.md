# MOTLEY_CUE
Mapper Oidc To Local idEntitY with loCal User managEment

## Usage
### Installation

- Install ldf_adapter: `pip install ldf_adapter-dist/feudalAdapter.tar.gz`
- Install motley_cue from pypi: `pip install motley_cue`
- Alternatively, install motley_cue from source:
    - Build package: `./setup.py sdist`
    - Install package: `pip install dist/motley_cue-$version.tar.gz`

### Configuration
See [mapper/config.py:reload](motley_cue/mapper/config.py) for a list of config file locations.

The config file can contain both the ldf_adapter settings, as well as mapper specific settings.

An example config file explaining the options can be found in [config_template.conf](config_template.conf).

When running from the current directory, the included symbolic links `./ldf_adapter.conf` and `./motley_cue.conf` are used as config files for `motley_cue` and `feudal-adapter`.

Alternatively, once can set the following environment variables:
```
export LDF_ADAPTER_CONFIG=$PWD/config_template.conf
export MOTLEY_CUE_CONFIG=$PWD/config_template.conf 
```

### Running
For quick testing, simply run with uvicorn (as user with permissions to add users) without TLS:

```sh
sudo motley_cue_uvicorn
```
The API will then be available at http://localhost:8080.

For example, the following commands deploy a local account for a given OIDC token, query the status of the local account, verify if a given username matches the local account mapped to a given token, and then undeploy the local account (without removing the home directory):
```sh
http http://localhost:8080/user/deploy  "Authorization: Bearer `oidc-token helmholtz-dev`"
http http://localhost:8080/user/get_status  "Authorization: Bearer `oidc-token helmholtz-dev`"
http http://localhost:8080/verify_user\?username\=diana_gudu  "Authorization: Bearer `oidc-token helmholtz-dev`"
http http://localhost:8080/user/undeploy  "Authorization: Bearer `oidc-token helmholtz-dev`"
```

We assume that the `oidc-agent` is running and has an account `helmholtz-dev` configured locally to retrieve the access token.

### Docker
The full setup with docker: [motley_cue_docker](https://github.com/dianagudu/motley_cue_docker) image.