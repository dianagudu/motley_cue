#!/bin/bash

cd testconf
curl -sSL https://git.io/get-mo -o mo
chmod +x mo

export EGI_TOKEN=`oidc-token https://aai.egi.eu/oidc/`
export HELMHOLTZ_DEV_TOKEN=`oidc-token https://login-dev.helmholtz.de/oauth2`
export WLCG_TOKEN=`oidc-token https://wlcg.cloud.cnaf.infn.it/`
export DEEP_TOKEN=`oidc-token https://iam.deep-hybrid-datacloud.eu`

export EGI_USER="c2370093c19496aeb46103cce3ccdc7b183f54ac9ba9c859dea94dfba23aacd5@egi.eu"
export HELMHOLTZ_DEV_VOS="urn:geant:helmholtz.de:group:Helmholtz-member#login-dev.helmholtz.de"

cat .env.mo | ./mo > .env
cat etc/motley_cue.conf.mo | ./mo > etc/motley_cue.conf

docker-compose up --build -d
docker-compose exec web pytest . -v