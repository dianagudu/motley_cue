#!/bin/bash

DEVSTRING="pr"
VERSION_FILE=motley_cue/VERSION

while [[ $# -gt 0 ]]; do
  case $1 in
    --devstring)
      DEVSTRING="$2"
      shift # past argument
      shift # past value
      ;;
    --version_file)
      VERSION_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

[ "x${CI}" == "xtrue" ] && {
    git config --global --add safe.directory "$PWD"
}

# Get master branch name:
#   use origin if exists
#   else use last found remote

MASTER_BRANCH=""
get_master_branch_of_mteam() {
    git remote -vv | awk -F[\\t@:] '{ print $1 " " $3 }' | while read REMOTE HOST; do 
        # echo " $HOST -- $REMOTE"
        MASTER=$(git remote show "$REMOTE"  2>/dev/null \
            | sed -n '/HEAD branch/s/.*: //p')
        MASTER_BRANCH="refs/remotes/${REMOTE}/${MASTER}"
        [ "x${HOST}" == "xcodebase.helmholtz.cloud" ] && {
            echo "${MASTER_BRANCH}"
            break
        }
        [ "x${HOST}" == "xgit.scc.kit.edu" ] && {
            echo "${MASTER_BRANCH}"
            break
        }
        [ "x${REMOTE}" == "xorigin" ] && {
            echo "${MASTER_BRANCH}"
            break
        }
    done
}
MASTER_BRANCH=$(get_master_branch_of_mteam)
PREREL=$(git rev-list --count HEAD ^"$MASTER_BRANCH")

# if we use a version file, things are easy:
[ -e $VERSION_FILE ] && {
    # version for python packages
    VERSION=$(cat $VERSION_FILE)
    PR_VERSION="${VERSION}.dev${PREREL}"
    echo "$PR_VERSION" > $VERSION_FILE
    echo "$PR_VERSION"
}

# if we store the version in debian changelog:
[ -e debian/changelog ] && {
    # get the latest version
    DEBIAN_VERSION=$(cat debian/changelog \
        | grep "(.*) " \
        | head -n 1 \
        | cut -d\( -f 2 \
        | cut -d\) -f 1)
    VERSION=$(echo "$DEBIAN_VERSION" | cut -d- -f 1)
    RELEASE=$(echo "$DEBIAN_VERSION" | cut -d- -f 2)
    PR_VERSION="${VERSION}~pr${PREREL}"
    VERSION_ESCAPED=$(echo ${VERSION} | sed s/\\\./\\\\./g); echo $VER
    sed s%${VERSION_ESCAPED}%${PR_VERSION}% -i debian/changelog
    #echo "$VERSION => $DEBIAN_VERSION + $DEBIAN_RELEASE => $PR_VERSION"
}

# lets see if RPM also needs a version to be set
SPEC_FILES=$(ls rpm/*spec)
[ -z "${SPEC_FILES}" ] || {
    [ -z "${VERSION}" ] || {
        PR_VERSION="${VERSION}~pr${PREREL}"
        for SPEC_FILE in $SPEC_FILES; do
            grep -q "$VERSION" "$SPEC_FILE" && { # version found, needs update
                VERSION_ESCAPED=$(echo ${VERSION} | sed s/\\\./\\\\./g); echo $VER
                sed "s/${VERSION_ESCAPED}/${PR_VERSION}/" -i "$SPEC_FILE"
            }
        done
        echo "$PR_VERSION"
    }
}
