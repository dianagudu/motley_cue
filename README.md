# MOTLEY_CUE
Mapper Oidc To Local idEntitY with loCal User managEment

## Installation

- Install motley_cue from pypi: `pip install motley_cue`
- Alternatively, install motley_cue from source:
    - Install prerequisites: `pip install -r requirements.txt`
    - Build package: `./setup.py sdist`
    - Install package: `pip install dist/motley_cue-$version.tar.gz`
- Debian package:
    ```
    apt-get install python3 python3-venv nginx
    dpkg -i motley-cue_$version.deb
    ```

## Configuration

Two configuration files are required:
- `motley_cue.conf`: contains configuration options specific to the REST API
- `ldf_adapter.conf`: contains configuration options for the [feudalAdapter](https://git.scc.kit.edu/feudal/feudalAdapterLdf)

### Configuration templates

An example config file explaining the options can be found in [etc/motley_cue.conf](etc/motley_cue.conf).

An example config for feudalAdapter is also included: [etc/ldf_adapter.conf](etc/ldf_adapter.conf).

### Config files search locations

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

## Running

### Development

For quick testing, simply run with uvicorn (as user with permissions to add users):

```sh
sudo motley_cue_uvicorn
```
The API will then be available at http://localhost:8080.

### Production

It is recommended to use:
- `gunicorn`: manages multiple uvicorn worker processes, monitors and restarts crashed processes
- `systemd`: service management and monitoring
- `nginx`: HTTPS support, buffers slow clients and prevents DoS attacks

If you installed `motley_cue` using the debian package, you can simply start the service by:
```sh
systemctl start motley-cue
```

This will start the `nginx` server too and serve requests on port 80.

For more details (or other Linux distributions), keep on reading.

#### gunicorn

To configure `motley_cue` to run with `gunicorn`, copy the following configuration files from `etc/` to `/etc/motley_cue`:
- `motley_cue.conf`
- `ldf_adapter.conf`
- `gunicorn.conf.py`: config file for gunicorn with sane default values.
- `motley_cue.env`: here you can set the environment variables used in the
gunicorn config, such as the socket address gunicorn listens on (`BIND`), 
log file location or log level.

#### systemd

Create the service files to run gunicorn under `systemd`.
Examples are provided with the debian package:
- [debian/motley-cue.service](debian/motley-cue.service)
- [debian/motley-cue.socket](debian/motley-cue.socket)

Copy the files to `/lib/systemd/system/motley-cue.service` and adapt them if 
necessary. The examples assume a python virtualenv at `/usr/lib/motley-cue`.

#### nginx

A site configuration is provided at [etc/nginx.motley_cue](etc/nginx.motley_cue). 
Copy it to the appropriate location and disable the default site if necessary.
```sh
cp etc/nginx.motley_cue /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/nginx.motley_cue /etc/nginx/sites-enabled/nginx.motley_cue
rm /etc/nginx/sites-enabled/default
```

It is highly recommented to use HTTPS. The site file also provides an example
configuration for that in the comments. You just need to generate certificates
for your server. Probably the simplest way to do that is by  using 
https://letsencrypt.org/.

## Usage

In the following we assume the API at http://localhost:8080/.

The Swagger UI, for interactive exploration, and to call and test your API
directly from the browser, can be reached at http://localhost:8080/docs.

You'll need an OIDC AccessToken to authenticate. Check out the
[oidc-agent](https://github.com/indigo-dc/oidc-agent) for that.

After you get the `oidc-agent` running, configure an account for your OP.
For example, if you generated an account named `helmholtz-dev` for the Helmholtz
AAI dev https://login-dev.helmholtz.de/, you can:
- deploy a local account for your federated identity:
  ```sh
  http http://localhost:8080/user/deploy  "Authorization: Bearer `oidc-token helmholtz-dev`"
  ```
- query the status of the local account, including your local username:
  ```sh
  http http://localhost:8080/user/get_status  "Authorization: Bearer `oidc-token helmholtz-dev`"
  ```
- verify if a given username matches the local account mapped to your remote identity
  ```sh
  http http://localhost:8080/verify_user\?username\=diana_gudu  "Authorization: Bearer `oidc-token helmholtz-dev`"
  ```
- suspend your local account (e.g. if you suspect your account has been
compromised):
  ```sh
  http http://localhost:8080/user/suspend "Authorization: Bearer `oidc-token helmholtz-dev`"
  ```


## Building the package in a docker container

To build the deb package for Debian testing, a Dockerfile is provided:
```
docker build --tag motley_cue_debianisation -f Dockerfile.build.debian .
```

The resulting files must be copied out of the build container to the `dist/debian` folder, using these commands:
```
mkdir -p dist/debian && docker run --rm motley_cue_debianisation tar -C /dist -c . | tar -C dist/debian -xv
```
