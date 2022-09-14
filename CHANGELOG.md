<a name="v0.4.0"></a>
# [v0.4.0](https://github.com/dianagudu/motley_cue/releases/tag/v0.4.0) - 14 Sep 2022

Features
=======
* add support for approval workflow #47 (feudal v0.5.0): update of `feudal_adapter.conf` required.

Enhancements
============
* support for CI on gitlab.scc.kit.edu 
* CI improvements: changelog from release, badges

Bug fixes
=======
* fix bug with non-conforming entitlements #48 (fixed in flaat v1.1.5) 

## What's Changed
* Changelog from release by @dianagudu in https://github.com/dianagudu/motley_cue/pull/40
* Add ci by @marcvs in https://github.com/dianagudu/motley_cue/pull/41
* Approval workflow by @dianagudu in https://github.com/dianagudu/motley_cue/pull/47
* **Full Changelog**: https://github.com/dianagudu/motley_cue/compare/v0.3.0...v0.4.0

[Changes][v0.4.0]


<a name="v0.3.0"></a>
# [v0.3.0](https://github.com/dianagudu/motley_cue/releases/tag/v0.3.0) - 09 May 2022

Features
=======
- add support for long-tokens (fixes #33) 

Enhancements
============
- add home_base option for local unix to feudal config (feudal v0.4.3)
- build package for centos 8

Bug fixes
========
- fix linting errors
- fix rpm packaging & make source rpms smaller by excluding unnecessary files
- fix required versions for dependencies

## What's Changed
* Fix centos8 docker target by @marcvs in https://github.com/dianagudu/motley_cue/pull/38
* Long tokens by @dianagudu in https://github.com/dianagudu/motley_cue/pull/39
* **Full Changelog**: https://github.com/dianagudu/motley_cue/compare/v0.2.1...v0.3.0

[Changes][v0.3.0]


<a name="v0.2.1"></a>
# [v0.2.1](https://github.com/dianagudu/motley_cue/releases/tag/v0.2.1) - 21 Mar 2022

Features
=======
- support additional local groups in feudal

Bug fixes
=======
- update supported Python versions (>= 3.7)
- fix package building for distributions where python >= 3.7 is not available by default

[Changes][v0.2.1]


<a name="v0.2.0"></a>
# [v0.2.0](https://github.com/dianagudu/motley_cue/releases/tag/v0.2.0) - 21 Mar 2022

Features
=======
- add support for LDAP backend in feudal (>=0.4.0)
- add support for audience checking for authorisation

Enhancements
============
- support new flaat version (>=1.0.0)
- add support for building rpms for rocky linux, centos stream, and stop supporting centos 8
- add ci workflow for running tests on push
- use black, pyright
- add badges to docs

Bug fixes
========
- fix linting errors
- fix duplicate groups for wlcg

[Changes][v0.2.0]


<a name="v0.1.5"></a>
# [v0.1.5](https://github.com/dianagudu/motley_cue/releases/tag/v0.1.5) - 21 Mar 2022

Add unit testing

[Changes][v0.1.5]


<a name="v0.1.4"></a>
# [v0.1.4](https://github.com/dianagudu/motley_cue/releases/tag/v0.1.4) - 21 Mar 2022

- add sphinx docs and publish to github-pages (via gh actions)
- add project logo
- update openapi schema with data models and validators
- disable swagger docs by default and make configurable

[Changes][v0.1.4]


<a name="v0.1.3"></a>
# [v0.1.3](https://github.com/dianagudu/motley_cue/releases/tag/v0.1.3) - 21 Mar 2022

- add google OP example to motley_cue.conf
- various fixes for error handling

[Changes][v0.1.3]


<a name="v0.1.2"></a>
# [v0.1.2](https://github.com/dianagudu/motley_cue/releases/tag/v0.1.2) - 21 Mar 2022

- copy wlcg.groups from AT to 'groups' claim for feudal
- fix #30 support non-jwt ops
- fix MapperResponse error for info authorisation with bad token
- fix #29 no more __pycache__ in /etc/motley_cue
- fix #26 add wlcg to default config
- fix #21: semodules only on centos, not removed on upgrade
- fixes for feudal logging
- add more logging for authorisation
- add suse rpm builds
- fix pam-ssh-oidc pkg name on deb, make it suggested instead of recommended


[Changes][v0.1.2]


<a name="v0.1.1"></a>
# [v0.1.1](https://github.com/dianagudu/motley_cue/releases/tag/v0.1.1) - 21 Mar 2022

- add service reload fix #17

[Changes][v0.1.1]


<a name="v0.1.0"></a>
# [v0.1.0](https://github.com/dianagudu/motley_cue/releases/tag/v0.1.0) - 21 Mar 2022

- fix #14 more flexible way to specify authorisation
- fix #15 individual user authorisation
- fix #18 more useful `/info` endpoint, without authentication
- add admin authorisation by sub+iss
- add examples for authorisation config for several OPs, default config authorises no one
- fix all calls to to_bool and to_list
- log level for motley_cue & gunicorn configured separately
- update login info in feudal_adapter.conf to use mccli

[Changes][v0.1.0]


<a name="v0.0.15"></a>
# [v0.0.15](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.15) - 21 Mar 2022

- add pooled accounts
- fix centos 7 build
- add selinux policies for centos

[Changes][v0.0.15]


<a name="v0.0.14"></a>
# [v0.0.14](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.14) - 21 Mar 2022

- fixes to rpm build

[Changes][v0.0.14]


<a name="v0.0.13"></a>
# [v0.0.13](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.13) - 21 Mar 2022

- rename ldf_adapter.conf to feudal_adapter.conf
- fix rpm build
- move service file to etc/

[Changes][v0.0.13]


<a name="v0.0.12"></a>
# [v0.0.12](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.12) - 21 Mar 2022

- reload nginx on motley-cue install

[Changes][v0.0.12]


<a name="v0.0.11"></a>
# [v0.0.11](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.11) - 21 Mar 2022

- support rpm pkg building
- fixes to deb builds
- install config files in /etc/motley_cue with deb pkg
- added config files to go in /etc on install to setup.cfg
- update readme with config file search locations
- use separate config files for motley_cue and ldf_adapter
- run gunicorn behind nginx, add nginx site configuration file
- bind gunicorn to unix socket instead of host and port


[Changes][v0.0.11]


<a name="v0.0.10"></a>
# [v0.0.10](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.10) - 21 Mar 2022

- better defaults and config templates
- remove unsupported distros
- now builds also with ubuntu-focal
- enforce python3
- read login_info from ldf_adapter CONFIG instead of mapper CONFIG
- use relative path to install files in etc/motley_cue


[Changes][v0.0.10]


<a name="v0.0.9"></a>
# [v0.0.9](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.9) - 10 Mar 2021

- update readme with info on nginx default site
- update readme with info on running motley_cue in production
- change log files default location and create dir when installing deb pkg
- add nginx configs to debian package
- run gunicorn behind nginx

[Changes][v0.0.9]


<a name="v0.0.8"></a>
# [v0.0.8](https://github.com/dianagudu/motley_cue/releases/tag/v0.0.8) - 10 Mar 2021

- add deb packaging
- update requirements.txt to use uvicorn[standard] which already includes uvloop and httptools

[Changes][v0.0.8]


[v0.4.0]: https://github.com/dianagudu/motley_cue/compare/v0.3.0...v0.4.0
[v0.3.0]: https://github.com/dianagudu/motley_cue/compare/v0.2.1...v0.3.0
[v0.2.1]: https://github.com/dianagudu/motley_cue/compare/v0.2.0...v0.2.1
[v0.2.0]: https://github.com/dianagudu/motley_cue/compare/v0.1.5...v0.2.0
[v0.1.5]: https://github.com/dianagudu/motley_cue/compare/v0.1.4...v0.1.5
[v0.1.4]: https://github.com/dianagudu/motley_cue/compare/v0.1.3...v0.1.4
[v0.1.3]: https://github.com/dianagudu/motley_cue/compare/v0.1.2...v0.1.3
[v0.1.2]: https://github.com/dianagudu/motley_cue/compare/v0.1.1...v0.1.2
[v0.1.1]: https://github.com/dianagudu/motley_cue/compare/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/dianagudu/motley_cue/compare/v0.0.15...v0.1.0
[v0.0.15]: https://github.com/dianagudu/motley_cue/compare/v0.0.14...v0.0.15
[v0.0.14]: https://github.com/dianagudu/motley_cue/compare/v0.0.13...v0.0.14
[v0.0.13]: https://github.com/dianagudu/motley_cue/compare/v0.0.12...v0.0.13
[v0.0.12]: https://github.com/dianagudu/motley_cue/compare/v0.0.11...v0.0.12
[v0.0.11]: https://github.com/dianagudu/motley_cue/compare/v0.0.10...v0.0.11
[v0.0.10]: https://github.com/dianagudu/motley_cue/compare/v0.0.9...v0.0.10
[v0.0.9]: https://github.com/dianagudu/motley_cue/compare/v0.0.8...v0.0.9
[v0.0.8]: https://github.com/dianagudu/motley_cue/tree/v0.0.8

 <!-- Generated by https://github.com/rhysd/changelog-from-release -->
