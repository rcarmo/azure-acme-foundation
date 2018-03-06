#!/bin/env python3
import yaml
import json
import sys
import os
import functools
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO,
                    format='>>> %(asctime)s %(levelname)s %(funcName)s:%(lineno)d\n---\n%(message)s\n---')
log = logging.getLogger()

def parse_config(filename):
    with open(filename, 'r') as stream:
        try:
            return yaml.load(stream)
        except yaml.YAMLError as exc:
            log.error(exc)
            exit(1)


def validate_config(config):
    # TODO - validate networking and flag machines without availability sets
    return config


def update_params(template, config, layerName):
    template['parameters']['tenantName'] = {
        "type": "string",
        "defaultValue": config['tenant']
    }
    template['parameters']['layerName'] = {
        "type": "string",
        "defaultValue": layerName
    }
    return template

def replace_variables(config, buffer, layerName, specs={}):
    specs = defaultdict(lambda: None, specs)
    log.debug(specs)
    replacements = [
        ('$LOCATION',       config['location']),
        ('$SUBNET',         layerName),
        ('$HOSTNAME',       specs['name']),
        ('$SIZE',           specs['size']),
        ('$SKU',            specs['sku']),
        ('$OSDISKSIZEGB',   specs['osDiskSizeGB']),
        ('$ADMINUSERNAME',  specs['adminUsername']),
        ('$ADMINPASSWORD',  specs['adminPassword']),
        ('$ADMINPUBLICKEY', specs['adminPublicKey'])
    ]
    for r in replacements:
        if r[1]:
            buffer = buffer.replace(r[0], str(r[1]))
    return buffer


def parse_snippet(config, filename, layerName, specs={}):
    with open('snippets/%s' % filename, 'r') as stream:
        return json.loads(replace_variables(config, stream.read(), layerName, specs))


def build_single_vm(config, layerName, specs):

    def replace_defaults(machine):
        for k in config['defaults']:
            if k not in machine:
                machine[k] = config['defaults'][k]
        return defaultdict(lambda: None, machine)

    specs = replace_defaults(specs)
    log.debug(specs)


    machine, nic = parse_snippet(config, '%s/vm.json' % specs['kind'], layerName, specs)
    if 'availabilitySet' in specs:
        machine['properties']['availabilitySet'] = {
            "id": "[resourceId('Microsoft.Compute/availabilitySets','%s')]" % specs['availabilitySet']
        }
        machine['dependsOn'].append("[concat('Microsoft.Compute/availabilitySets/','%s')]" % specs['availabilitySet']
)

    if 'oms' in config and config['oms']:
        machine['resources'].append(parse_snippet(config, '%s/oms.json' % specs['kind'], layerName, specs))

    if 'sql' in specs and specs['sql']:
        machine['resources'].append(parse_snippet(config, '%s/sql.json' % specs['kind'], layerName, specs))

    if 'dataDisks' in specs: # TODO: revise for larger sets
        defaults = {
            "createOption": "Empty",
            "diskSizeGB": "1023",
            "caching": "ReadOnly",
            "managedDisk": {
                "storageAccountType": "Premium_LRS"
            }
        }
        disks = []
        for d in specs['dataDisks']:
            disk = dict(defaults)
            disk.update(dict(d))
            disks.append(disk)
        machine['properties']['storageProfile']['dataDisks'] = disks

    # TODO: "customData": "[parameters('serverCustomData')]",
    # TODO: imageReference with SKUs, offer
    return [machine, nic]


def build_monitoring(config):
    layerName = 'monitoring'
    template = parse_snippet(config, 'template.json', layerName)    
    template['variables'] = parse_snippet(config, 'variables.json', layerName)
    template['resources'] = parse_snippet(config, 'monitoring/resources.json', layerName)

    if 'oms' in config and config['oms']:
       template['resources'] += parse_snippet(config, 'monitoring/oms.json', layerName)
       template['variables'].update(parse_snippet(config, 'monitoring/variables.json', layerName))
    return update_params(template, config, layerName)


def build_networking(config):

    def extract_subnets(config):
        subnets = []
        for l in config['layers']:
            if 'addressing' in l:
                subnets.append({
                    "name": l['name'],
                    "properties": {
                        "addressPrefix": l['addressing']
                    }
                })
        return subnets

    layerName = 'networking'
    networking = parse_snippet(config, 'networking/template.json', layerName)    
    networking['properties']['addressSpace']['addressPrefixes'] = [config['addressing']]
    networking['properties']['subnets'] = extract_subnets(config)

    template = parse_snippet(config, 'template.json', layerName)    
    template['variables'] = parse_snippet(config, 'variables.json', layerName)
    template['resources'] = [networking]

    return update_params(template, config, layerName)


def build_single_layer(config, specs):
    log.debug(json.dumps(specs, indent=4))
    availabilitySets = {}
    machines = []
    layerName = specs['name']

    if 'machines' in specs:
        for m in specs['machines']:
            if 'availabilitySet' in m:
                name = m['availabilitySet']
                if name not in availabilitySets:
                    availabilitySets[name]=parse_snippet(config, 'availabilityset.json', layerName, {'name': name})
                availabilitySets[name]['properties']['virtualMachines'].append({"id": "[resourceId('Microsoft.Compute/virtualMachines','%s')]" % m['name']})

        for m in specs['machines']:
            machines.extend(build_single_vm(config, specs['name'], m))
    
    template = parse_snippet(config, 'template.json', layerName)    
    template['variables'] = parse_snippet(config, 'variables.json', layerName)
    template['resources'] += machines
    template['resources'] += map(lambda x: x[1], availabilitySets.items())

    return update_params(template, config, specs['name'])

def build_generic_layers(config):
    for layer in config['layers']:
        if 'machines' in layer: # only do IaaS for now
            with open('templates/%s-%s.json' % (config['tenant'], layer['name']), 'w') as stream:
                json.dump(build_single_layer(config, layer), stream, indent=4)


def generate(config):
    # build the networking layer first
    tenant = config['tenant']
    with open('templates/%s-networking.json' % tenant, 'w') as stream:
        json.dump(build_networking(config), stream, indent=4)
    with open('templates/%s-monitoring.json' % tenant, 'w') as stream:
        json.dump(build_monitoring(config), stream, indent=4)
    build_generic_layers(config)


if __name__=='__main__':
    generate(validate_config(parse_config(sys.argv[1])))