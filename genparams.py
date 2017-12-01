#!/bin/env python3 
from base64 import b64encode
from os import environ
from json import dumps
from string import Template

def slurp(filename):
    # parse a YAML file and replace ${VALUE}s
    t = Template(open("cloud-config/" + filename, "r").read())
    return b64encode(bytes(t.substitute(environ),'utf-8')).decode()

# common parameters for all layers of the stack
defaults = {
    "tenantName": {
        "value": environ['TENANT_NAME']
    },
    "adminUsername": {
        "value": environ['SSH_USER']
    },
    "adminPublicKey": {
        "value": open("keys/" + environ['SSH_USER'] + ".pub","r").read()
    }
}

params = {
    "foundation": {**defaults, **{ # idiomatic dictionary merge
        "jumpBoxCustomData": {
            "value": slurp('jumpbox.yml')
        },
        "servicesTag": {
            "value": "ssh"
        },
        "diagStorageType": {
            "value": "Standard_LRS"
        },
        "serverSubnet": {
            "value": "devops"
        }
    }},
    "data": {**defaults, **{ 
        "layerName": {
            "value": "data"
        },
        "serverCustomData": {
            "value": slurp('data.yml')
        },
        "servicesTag": {
            "value": "ssh,cockroachdb"
        },
        "serverSubnet": {
            "value": "data"
        }
    }},
    "middleware": {**defaults, **{
        "serverCustomData": {
            "value": slurp('middleware.yml')
        },
        "servicesTag": {
            "value": "ssh,http"
        },
        "serverSubnet": {
            "value": "middleware"
        }
    }},
    "frontend": {**defaults, **{ 
        "frontEndServerCustomData": {
            "value": slurp('frontend.yml')
        }
    }},
    "devops": {**defaults, **{ 
        "devopsCustomData": {
            "value": slurp('devops.yml')
        }
    }},
}

for k in params.keys():
    with open('parameters/' + k + '.json', 'w') as h:
        h.write(dumps(params[k]))
