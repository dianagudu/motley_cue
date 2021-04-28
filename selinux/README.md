# SELINUX

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

