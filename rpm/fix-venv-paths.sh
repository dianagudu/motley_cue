#!/bin/bash

DESTDIR=$1
PKG_NAME=$2

for FILE in ${DESTDIR}/usr/lib/${PKG_NAME}/bin/*; do
    test -L $FILE || {
        echo "Fixing venv path in $FILE"
        sed s@${DESTDIR}@@g -i $FILE
    }
done
