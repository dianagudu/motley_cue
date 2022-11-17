#!/bin/bash

VERSION_FILE=motley_cue/VERSION


[ "x${CI}" == "xtrue" ] && {
    git config --global --add safe.directory "$PWD"
}

# Get master branch name:
#   use origin if exists
#   else use last found remote
REMOTES=$(git remote show)
for R in $REMOTES; do
    MASTER=$(git remote show $R  2>/dev/null \
        | sed -n '/HEAD branch/s/.*: //p')
    MASTER_BRANCH="refs/remotes/${R}/${MASTER}"
    #echo "Master-branch: ${MASTER_BRANCH}"
    [ "x$R" == "xorigin" ] && break
done

PREREL=$(git rev-list --count HEAD ^$MASTER_BRANCH)

# if we use a version file, things are easy:
[ -e $VERSION_FILE ] && {
    VERSION=$(cat $VERSION_FILE)
    PR_VERSION="${VERSION}.dev${PREREL}"
    echo "$PR_VERSION" > $VERSION_FILE
}

# if we store the version in debian changelog:
[ -e debian/changelog ] && {
    # get the latest version
    VERSION=$(cat debian/changelog \
        | grep "(.*) " \
        | head -n 1 \
        | cut -d\( -f 2 \
        | cut -d\) -f 1)
    DEBIAN_VERSION=$(echo $VERSION | cut -d- -f 1)
    DEBIAN_RELEASE=$(echo $VERSION | cut -d- -f 2)
    PR_VERSION="${DEBIAN_VERSION}-pr${PREREL}-${DEBIAN_RELEASE}"
    sed s%${VERSION}%${PR_VERSION}% -i debian/changelog
    #echo "$VERSION => $DEBIAN_VERSION + $DEBIAN_RELEASE => $PR_VERSION"
}

# lets see if RPM also needs a version to be set
SPEC_FILES=$(ls rpm/*spec)
[ -z "${SPEC_FILES}" ] || {
    [ -z ${VERSION} ] || {
        for SPEC_FILE in $SPEC_FILES; do
            grep -q $VERSION $SPEC_FILE && { # version found, needs update
                sed s%${VERSION}%${PR_VERSION}% -i $SPEC_FILE
            }
        done
    }
}
echo ${PR_VERSION}