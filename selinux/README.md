# SELINUX

Note, the following configuration is working for Centos8, but not for
Centos7. If you can contribute changes for supporting this, don't hesitate
to contact us via ssh-oidc@lists.kit.edu, or to send a PR to https://github.com/dianagudu/motley_cue

# Install se modules

semodule -i motley-cue-gunicorn.pp
semodule -i motley-cue-sshd.pp
semodule -i motley-cue-nginx.pp
setsebool -P nis_enabled 1

# Uninstall se modules

semodule -r motley-cue-gunicorn
semodule -r motley-cue-nginx
semodule -r motley-cue-sshd
setsebool -P nis_enabled 0

