#!/bin/bash

DESTDIR=$1
PKG_NAME=$2
VENV_BASE=$3

VENV_PATH="${VENV_BASE}/venv"
TOPATH="/usr/lib/${PKG_NAME}"

for FILE in "${DESTDIR}/usr/lib/${PKG_NAME}"/bin/*; do
    test -L "$FILE" && continue
    echo "Fixing venv path in $FILE"
    # Console scripts copied from the venv built under the source dir carry a
    # "<srcdir>/venv/bin/python" shebang.
    sed -i "s@${VENV_PATH}@${TOPATH}@g" "$FILE"
    # Scripts (re)created by pip during "make install" - e.g. motley_cue_uvicorn -
    # are run through the buildroot interpreter, so pip bakes the buildroot path
    # into their shebang. Strip the buildroot prefix so check-buildroot passes.
    sed -i "s@${DESTDIR}@@g" "$FILE"
done

# Recompile bytecode so the path recorded in each .pyc is the runtime path
# rather than the buildroot path pip used during install. Otherwise
# check-buildroot aborts on .pyc files that still embed the buildroot.
# Stripping the buildroot here also normalises the dependency .pyc that were
# compiled under the source venv.
PYTHON_BIN="${DESTDIR}/usr/lib/${PKG_NAME}/bin/python"
if [ -x "$PYTHON_BIN" ]; then
    "$PYTHON_BIN" -m compileall -q -f -s "$DESTDIR" "${DESTDIR}/usr/lib/${PKG_NAME}" || true
fi
