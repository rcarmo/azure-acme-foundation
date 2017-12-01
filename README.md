# Azure ACME Foundation Templates

<a href="//en.wikipedia.org/wiki/File:Box_of_%22ACME_EXPLOSIVE_TENNIS_BALLS%22_(screencap).jpg" title="Fair use of copyrighted material in the context of Acme Corporation">
<img src="https://upload.wikimedia.org/wikipedia/en/8/84/Box_of_%22ACME_EXPLOSIVE_TENNIS_BALLS%22_%28screencap%29.jpg"></a>

## TODO

* [ ] Key vault
* [ ] Service Map agent
* [ ] Front-end load balancers
* [ ] Docker registry and Jenkins
* [ ] Postgres PaaS
* [ ] Check timezones and locales in cloud-config
* [ ] Tag solutions and OMS
* [x] Timestamp deployments
* [x] Full diagnostics and OMS configuration (solutions, dashboards, container support)
* [x] Docker CE repository added to all servers to ease deployment
* [x] Generic layer template
* [x] Jumpbox and diagnostics storage account
* [x] Networking

> **Note:** Right now all VMs start a `redis` container for testing OMS monitoring. That will be removed in the future.

## What

This is a set of scripts to generate and deploy Azure Resource Manager templates for multi-tier, multi-tenant solutions.

A `tenant` is defined as a set of resource groups, each of which maps to a typical application tier or environment:

* `foundation` (networking, OMS monitoring and an SSH jumpbox)
* `data` (IaaS database servers)
* `middleware` (app servers)
* `frontend` (front-end servers)
* `devops` (Jenkins, etc.)

This is what it all looks like deployed, if you hide away storage and other inconsequentials:

<img src="https://raw.githubusercontent.com/rcarmo/azure-acme-foundation/master/images/overview.png" style="max-width: 100%; height: auto;">

## Why

I needed a set of re-usable Azure templates that brought together a number of (sometimes quite widely disseminated) aspects of Linux infrastructure management in Azure and that enabled me to get large-scale projects up to speed quickly.

As such, these templates have a number of distinguishing features from the standard Microsoft samples:

* _Everything_ is CLI-driven. Templates never leave your machine and are _never_ published to a public URL
* All layes share a foundation networking infrastructure and can be developed/tweaked independently
* Server configurations include full Linux/Docker diagnostics, logging and monitoring, including a free tier OMS instance and sample dashboards
* Linux package provisioning leverages `cloud-config`, making it easier to re-use existing on-premises (or competing providers') configurations

Why ACME? well, because I loved the Warner Bros. cartoons, and because these templates aim to let to do _everything_ you'd possibly need to get your infrastructure running and usable in under an hour.

## How

* `make keys` - generates an SSH key for managing the servers
* `make params` - generates ARM template parameters
* `make deploy-foundation` - deploys the networking layer, the jumpbox, a diagnostics storage account and OMS for all servers
* `make deploy-<layername>` - deploys a named layer using the `generic-layer` template
* `make endpoints` - list DNS aliases
* `make destroy-<layername>` - destroys the named layer

## Recommended Sequence

    # edit the Makefile to set the tenant name
    # edit genparams.py to map layers to cloud-config files, set tags, etc.
    az login
    make keys
    make params
    make deploy-foundation
    make deploy-data
    make deploy-middleware
    make deploy-frontend
    make endpoints
    make ssh

## Requirements

* GNU `make`
* [Python 3][p]
* The new [Azure CLI](https://github.com/Azure/azure-cli) (`pip install -U azure-cli` will install it)

[d]: http://docker.com
[p]: http://python.org
[dh]:https://hub.docker.com/r/rcarmo/demo-frontend-stateless/
