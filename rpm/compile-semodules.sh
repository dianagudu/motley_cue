#!/bin/bash

DESTDIR=$1

for MODULE in motley-cue-gunicorn motley-cue-nginx motley-cue-sshd; do
    test -L ${DESTDIR}/${MODULE}.te || {
        echo "Compiling se module ${MODULE}"
        checkmodule -M -m -o ${DESTDIR}/${MODULE}.mod ${DESTDIR}/${MODULE}.te
        semodule_package -o ${DESTDIR}/${MODULE}.pp -m ${DESTDIR}/${MODULE}.mod
        rm -rf ${DESTDIR}/${MODULE}.mod
    }
done