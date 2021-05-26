#!/bin/bash

DESTDIR=$1
PKG_NAME=$2

FROMPATH="/tmp/build/motley_cue/venv"
TOPATH="/usr/lib/motley-cue"

for FILE in ${DESTDIR}/usr/lib/${PKG_NAME}/bin/*; do
    test -L $FILE || {
        echo "Fixing venv path in $FILE"
        sed s@${FROMPATH}@${TOPATH}@g -i $FILE
    }
done
