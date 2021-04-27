# Install se modules

semodule -X 300 -i motley-cue-gunicorn.pp
semodule -X 400 -i motley-cue-sshd.pp
setsebool -P nis_enabled 1

# Uninstall se modules

semodule -e motley-cue-gunicorn
semodule -e motley-cue-sshd
setsebool -P nis_enabled 0

