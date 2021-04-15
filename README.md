# MOTLEY_CUE
Mapper Oidc To Local idEntitY with loCal User managEment

## Installation

- Install motley_cue from pypi: `pip install motley_cue`
- Alternatively, install motley_cue from source:
    - Install prerequisites: `pip install -r requirements.txt`
    - Build package: `./setup.py sdist`
    - Install package: `pip install dist/motley_cue-$version.tar.gz`
- Debian package from http://repo.data.kit.edu/:
    ```
    curl repo.data.kit.edu/key.pgp | apt-key add -
    apt-get install motley-cue
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

This will start the `nginx` server too and serve requests on port 8080.

You can change the port and other nginx settings by editing `/etc/nginx/sites-enabled/nginx.motley_cue`.

For more details about setting up the production instance, keep on reading.

#### gunicorn

To configure `motley_cue` to run with `gunicorn`, copy the following configuration files from `etc/` to `/etc/motley_cue`:
- `motley_cue.conf`
- `ldf_adapter.conf`
- `gunicorn.conf.py`: config file for gunicorn with sane default values.
- `motley_cue.env`: here you can set the environment variables used in the gunicorn config, such as the socket address gunicorn listens on (`BIND`), log file location or log level.

#### systemd

Create the service files to run gunicorn under `systemd`.
Examples are provided with the debian package:
- [debian/motley-cue.service](debian/motley-cue.service)
- [debian/motley-cue.socket](debian/motley-cue.socket)

Copy the files to `/lib/systemd/system/motley-cue.service` and adapt them if 
necessary. The examples assume a python virtualenv at `/usr/lib/motley-cue`.

#### nginx

A site configuration is provided at [etc/nginx.motley_cue](etc/nginx.motley_cue). 
Copy it to the appropriate location:
```sh
cp etc/nginx.motley_cue /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/nginx.motley_cue /etc/nginx/sites-enabled/nginx.motley_cue
```

It is highly recommended to use HTTPS. The site file also provides an example
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
For example, if you generated an account named `egi` for the [EGI AAI](https://aai.egi.eu/oidc), you can:
- deploy a local account for your federated identity:
  ```sh
  http http://localhost:8080/user/deploy  "Authorization: Bearer `oidc-token egi`"
  ```
- query the status of the local account, including your local username:
  ```sh
  http http://localhost:8080/user/get_status  "Authorization: Bearer `oidc-token egi`"
  ```
- verify if a given username matches the local account mapped to your remote identity
  ```sh
  http http://localhost:8080/verify_user\?username\=diana_gudu  "Authorization: Bearer `oidc-token egi`"
  ```
- suspend your local account (e.g. if you suspect your account has been
compromised):
  ```sh
  http http://localhost:8080/user/suspend "Authorization: Bearer `oidc-token egi`"
  ```


## Building the package in a docker container

To build the supported packages, a Makefile is provided, which uses docker
for building:
```
make dockerised_<name>
```
Where `<name>` can be one of:
- `debian_buster`
- `debian_bullseye`
- `ubuntu_bionic`
- `ubuntu_focal`
- `centos8`
- all_packages (to build all of the above)

The resulting files are copied out of the build container to the `../results` folder.

## SSH Integration

### PAM

You'll need [this](https://git.man.poznan.pl/stash/scm/pracelab/pam.git) PAM module that supports OIDC authentication by prompting the user for a token instead of a password.

You can also install it from the http://repo.data.kit.edu/ repo:
```sh
apt-get install pam-ssh-oidc
```

Check out the documentation for how to configure it. Make sure you set ssh to use the PAM module.

In `/etc/pam.d/sshd` add on the first line:
```sh
auth     sufficient pam_oidc_token.so config=/etc/pam.d/config.ini
```
and configure the verification endpoint to your motley_cue instance in `/etc/pam.d/config.ini`:
```
[user_verification]
local = false
verify_endpoint = $MOTLEY_CUE_ENDPOINT/verify_user
```
where MOTLEY_CUE_ENDPOINT=<http://localhost:8080> with a default installation.

Finally, make sure you have in your `/etc/ssh/sshd_config`:
```
ChallengeResponseAuthentication yes
UsePam yes
```

### Client

To ssh into a server that supports OIDC authentication, you'll need to trigger the deployment of a local account by calling the /deploy endpoint and then getting the local username.

Of you can have a look at this SSH client wrapper that does all this for you: https://github.com/dianagudu/mc_ssh.
