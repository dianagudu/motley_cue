# MOTLEY_CUE
Mapper Oidc To Local idEntitY with loCal User managEment

## Usage
### Installation

- Install ldf_adapter: `pip install ldf_adapter-dist/ldf_adapter-0.1.2.dev1.tar.gz`
- Build package: `./setup.py sdist`
- Install package: `pip install dist/motley_cue-$version.tar.gz`

### Configuration
See [mapper/config.py:reload](motley_cue/mapper/config.py) for a list of config file locations.

The config file can contain both the ldf_adapter settings, as well as mapper specific settings.

An example config file explaining the options can be found in [config_template.conf](config_template.conf).

Example usage:

```
export LDF_ADAPTER_CONFIG=$PWD/config_template.conf                                                          
export MOTLEY_CUE_CONFIG=$PWD/config_template.conf 
```

### Running
For quick testing, simply run with uvicorn:

```sh
motley_cue_uvicorn
```

