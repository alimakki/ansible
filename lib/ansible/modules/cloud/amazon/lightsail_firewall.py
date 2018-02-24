#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'metadata_version': '1.0'}

DOCUMENTATION = '''
---
module: lightsail_firewall
short_description: Manage Amazon Lightsail's firewall for a given instance
description:
     - Manage's a running instance's firewall
version_added: "2.4"
author: "Ali Makki (@alimakki)"

'''


EXAMPLES = '''

'''

import os
import time
import traceback

try:
    import botocore
    HAS_BOTOCORE = True
except ImportError:
    HAS_BOTOCORE = False

try:
    import boto3
except ImportError:
    # will be caught by imported HAS_BOTO3
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import ec2_argument_spec, get_aws_connection_info, boto3_conn, HAS_BOTO3, camel_dict_to_snake_dict

def open_port(module, client, from_port, to_port, protocol, instance_name):
    changed = False

    try:
        resp = client.open_instance_public_ports(
            portInfo={
                'fromPort': from_port,
                'toPort':   to_port,
                'protocol': protocol
                },
            istanceName=instance_name
        )
        changed = True
    except as e:
        module.fail_json(msg='Error opening ports for instance {0}, error: {1}'.format(instance_name, e))

    return (changed, resp)

def close_port(module, client, from_port, to_port, protocol, instance_name):
    changed = False

    try:
        resp = client.close_instance_public_ports(
            portInfo={
                'fromPort': from_port,
                'toPort':   to_port,
                'protocol': protocol
                },
            istanceName=instance_name
        )
        changed = True
    except as e:
        module.fail_json(msg='Error closing ports for instance {0}, error: {1}'.format(instance_name, e))

    return (changed, resp)
    
def core(module):
    region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
    if not region:
        module.fail_json(msg='region must be specified')

    client = None

    try:
        client = boto3_conn(module, conn_type='client', resource='lightsail',
                           region=region, endpoint=ec2_url, **aws_connect_kwargs)
        
    except (botocore.exceptions.ClientError, botocore.exceptions.ValidationError) as e:
        module.fail_json('Failed while connecting to the lightsail service: %s' % e, exception=traceback.format_exc())

    changed = False
    state = module.params['state']
    from_port = module.params['from_port')
    to_port = module.params['to_port']
    protocol = module.params['protocol']
    instance_name = module.params['name]

    if state == 'absent':
        changed, key_pair_dict = close_port(module, client, from_port, to_port, protocol, instance_name)
    elif state == 'present':
        changed, key_pair_dict = open_port(module, client, from_port, to_port, protocol, instance_name)

    module.exit_json(changed=changed, instance=camel_dict_to_snake_dict(key_pair_dict))

def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        protocol=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        from_port=dict(type='int', required=True),
        to_port=dict(type='int', required=True),
        protocol=dict(type'str', required=True)
    ))

    module = AnsibleModule(argument_spec=argument_spec)

    if not HAS_BOTO3:
        module.fail_json(msg='Python module "boto3" is missing, please install it')

    if not HAS_BOTOCORE:
        module.fail_json(msg='Python module "botocore" is missing, please install it')

    try:
        core(module)
    except (botocore.exceptions.ClientError, Exception) as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())

if __name__ == '__main__':
    main()