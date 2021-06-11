## Configuration for motley_cue

########
[mapper]
########
## various service-specific settings
##
## log_level -- default: WARNING
log_level = WARNING
##
## audience claim specific to this service
## NOT SUPPORTED
# audience = <ssh_host>

#########
[DEFAULT]
#########
## Magic section that provides default values for all sections below.
## These values are overwritten by values in each section, if specified.
## DO NOT CHANGE this section unless you really want to apply the changes to ALL OPs.
##
## this is the only key without a default value, must be specified for each section
# op_url =
##
######################
## USER AUTHORISATION
######################
## authorise all users from trusted OP, defaults to False if not specified
authorise_all = False
## list of VOs whose users are authorised to use the service
authorised_vos = []
## the OIDC claim containing the VOs specified above
vo_claim = eduperson_entitlement
## how many VOs need to be matched from the list, valid options: all, one, or an int
## defaults to one if not specified
vo_match = one
## list of individual users authorised to use the service
## specified through OIDC 'sub', relative to the section's OP ('iss')
## defaults to empy list if not specified
authorised_users = []
##
## You can find out your 'sub' and VOs you are a member of by using flaat:
##      $ pip install flaat
##      $ flaat-userinfo $TOKEN
## where $TOKEN contains an Access Token from the OP you are interested it.
## A commandline tool to retrieve access tokens is:
##      oidc-agent [https://github.com/indigo-dc/oidc-agent]
##
#################################################################################
## ADMIN AUTHORISATION
##
## Each OP includes authorisation for the /admin endpoint,
## which allows suspending and resuming access for given users.
##
## Currently, only individual admins can be authorised (by 'sub' claim).
## This is meant for infrastructure security contacts.
## In the future, we plan to support this feature for VO managers too, to suspend
## members of their own VO (by using VO roles encoded in AARC-G002 entitlements).
##################################################################################
## list of authorised admins
authorised_admins = []
## allow admins to suspend users from any OP
## defaults to False, which means an admin can only suspend users from their own OP
# authorise_admins_for_all_ops = False




#########################################################################################
## AUTHORISATION PER OIDC PROVIDER
##
## The following sections are used to configure auhtorisation of users from multiple OPs.
## Any section named [authorisation.*] configures the authorisation for a single OP.
##
## Feel free to add more sections to support your desired OPs.
## You can overwrite any of the default values by simply specifying a new value.
## Take a look at the examples in the comments to help get you started.
#########################################################################################

###################
[authorisation.wlcg]
###################
## AUTHORISE ALL
op_url = https://wlcg.cloud.cnaf.infn.it/

## USER AUTHORISATION
authorise_all = True


###################
[authorisation.egi]
###################
## INDIVIDUAL AUTHORISATION
op_url = https://aai.egi.eu/oidc

## USER AUTHORISATION
authorised_users = [
        "{{EGI_USER}}"
    ]

## ADMIN AUTHORISATION
## In this example, the three admins specified below can suspend any user on this service.
authorised_admins = [
        "{{EGI_USER}}"
    ]
authorise_admins_for_all_ops = True


#############################
[authorisation.helmholtz-dev]
#############################
## VO-BASED AUTHORISATION
op_url = https://login-dev.helmholtz.de/oauth2

## USER AUTHORISATION
## In this example, the user has to be a member of all the specified VOs.
authorised_vos = {{HELMHOLTZ_DEV_VOS}}


####################
[authorisation.deep]
####################
## SUPPORTED but NOT AUTHORISED
op_url = https://iam.deep-hybrid-datacloud.eu


###################
# [authorisation.kit]
###################
## NOT SUPPORTED
# op_url = https://oidc.scc.kit.edu/auth/realms/kit

