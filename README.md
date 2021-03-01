# MOTLEY_CUE
Mapper Oidc To Local idEntitY with loCal User managEment

## Usage
### Installation

- Install motley_cue from pypi: `pip install motley_cue`
- Alternatively, install motley_cue from source:
    - Build package: `./setup.py sdist`
    - Install package: `pip install dist/motley_cue-$version.tar.gz`

### Configuration

Two configuration files are required:
- `motley_cue.conf`: contains configuration options specific to the REST API
- `ldf_adapter.conf`: contains configuration options for the [feudalAdapter](https://git.scc.kit.edu/feudal/feudalAdapterLdf)

#### Configuration templates

An example config file explaining the options can be found in [etc/motley_cue.conf](etc/motley_cue.conf).

An example config for feudalAdapter is also included: [etc/ldf_adapter.conf](etc/ldf_adapter.conf).

#### Config files search locations

The config file `motley_cue.conf` will be searched in several places. Once it is found no further config files will be considered:

- First, the environment variable `MOTLEY_CUE_CONFIG` is used
- If that does not work, these files will be tried by default:
    - `motley_cue.conf`
    - `$HOME/.config/motley_cue/motley_cue.conf`
    - `/etc/motley_cue/motley_cue.conf`

Similar search locations are used for `ldf_adapter.conf`, according to the feudalAdapter documentation:
- the environment variable `LDF_ADAPTER_CONFIG`
- `ldf_adapter.conf`
- `$HOME/.config/ldf_adapter.conf`
- `$HOME/.config/feudal/ldf_adapter.conf`
- `/etc/feudal/ldf_adapter.conf`

### Running
For quick testing, simply run with uvicorn (as user with permissions to add users):

```sh
sudo motley_cue_uvicorn
```
The API will then be available at http://localhost:8080.

### Usage

For example, the following commands deploy a local account for a given OIDC token, query the status of the local account, verify if a given username matches the local account mapped to a given token, and then suspend the local account:
```sh
http http://localhost:8080/user/deploy  "Authorization: Bearer `oidc-token helmholtz-dev`"
http http://localhost:8080/user/get_status  "Authorization: Bearer `oidc-token helmholtz-dev`"
http http://localhost:8080/verify_user\?username\=diana_gudu  "Authorization: Bearer `oidc-token helmholtz-dev`"
http http://localhost:8080/user/suspend "Authorization: Bearer `oidc-token helmholtz-dev`"
```

We assume that the `oidc-agent` is running and has an account `helmholtz-dev` configured locally to retrieve the access token.

### Docker
The full setup with docker: [motley_cue_docker](https://github.com/dianagudu/motley_cue_docker) image.
