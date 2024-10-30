#!/bin/bash

echo -n "python3 version: "
python3 --version
# # Tweak python versions for some distros:
#
# case "${DISTRO}-${RELEASE}" in
#     rockylinux-8|almalinux-8)
#         [ -e /bin/python3.11 ] && {
#             echo "setting python3.11 as a default for python3"
#             cd /etc/alternatives
#             rm python3
