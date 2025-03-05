#!/bin/bash

echo "### local-before-script.sh #####################################"
echo -n "python3 version: "
python3 --version
ls -l `which python3`
ls -l /etc/alternatives/python3*
ls -l /usr/bin/python3*

# # Tweak python versions for some distros:
#
# case "${DISTRO}-${RELEASE}" in
#     rockylinux-8|almalinux-8)
#         [ -e /bin/python3.11 ] && {
#             echo "setting python3.11 as a default for python3"
#             cd /etc/alternatives
#             rm python3
echo "END local-before-script.sh #####################################"
