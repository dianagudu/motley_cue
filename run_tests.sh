#!/bin/bash

### Requirements
## you'll need to have the following installed:
##     * flaat: `pip install flaat`
##     * docker
##     * docker-compose
##     * jq
##     * curl
##     * oidc-agent
## and oidc-agent accounts configured for the following OPs:
##     https://aai.egi.eu/oidc/`
##     https://login-dev.helmholtz.de/oauth2`
##     https://wlcg.cloud.cnaf.infn.it/`
##     https://iam.deep-hybrid-datacloud.eu`
##     https://oidc.scc.kit.edu/auth/realms/kit`

function get_sub {
    token=$1
    echo `flaat-userinfo --userinfo $token | grep -v "Token valid for" | jq -c -r .sub`
}

function get_vos {
    token=$1
    claim=$2
    echo `flaat-userinfo --userinfo $token | grep -v "Token valid for" | jq -c -r .$claim`
}

cd testconf

export EGI_TOKEN=`oidc-token https://aai.egi.eu/oidc/`
export HELMHOLTZ_DEV_TOKEN=`oidc-token https://login-dev.helmholtz.de/oauth2`
export WLCG_TOKEN=`oidc-token https://wlcg.cloud.cnaf.infn.it/`
export DEEP_TOKEN=`oidc-token https://iam.deep-hybrid-datacloud.eu`
export KIT_TOKEN=`oidc-token https://oidc.scc.kit.edu/auth/realms/kit`

export EGI_USER=`get_sub $EGI_TOKEN`
export HELMHOLTZ_DEV_VOS=`get_vos $HELMHOLTZ_DEV_TOKEN eduperson_entitlement`

curl -sSL https://git.io/get-mo -o mo && chmod +x mo
cat .env.mo | ./mo > .env
cat motley_cue.conf.mo | ./mo > motley_cue.conf

docker-compose up --build -d
docker-compose exec web pytest . -v

rm .env motley_cue.conf