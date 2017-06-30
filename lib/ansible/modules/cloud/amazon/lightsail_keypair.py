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
module: lightsail
short_description: Create or delete a virtual machine instance in AWS Lightsail
description:
     - Creates or instances in AWS Lightsail and optionally wait for it to be 'running'.
version_added: "2.4"
author: "Nick Ball (@nickball)"
options:
  state:
    description:
      - Indicate desired state of the target.
    default: present
    choices: ['present', 'absent', 'running', 'restarted', 'stopped']
  name:
    description:
      - Name of the instance
    required: true
    default : null
  zone:
    description:
      - AWS availability zone in which to launch the instance. Required when state='present'
    required: false
    default: null
  blueprint_id:
    description:
      - ID of the instance blueprint image. Required when state='present'
    required: false
    default: null
  bundle_id:
    description:
      - Bundle of specification info for the instance. Required when state='present'
    required: false
    default: null
  user_data:
    description:
      - Launch script that can configure the instance with additional data
    required: false
    default: null
  key_pair_name:
    description:
      - Name of the key pair to use with the instance
    required: false
    default: null
  wait:
    description:
      - Wait for the instance to be in state 'running' before returning.  If wait is "no" an ip_address may not be returned
    default: "yes"
    choices: [ "yes", "no" ]
  wait_timeout:
    description:
      - How long before wait gives up, in seconds.
    default: 300

requirements:
  - "python >= 2.6"
  - boto3

extends_documentation_fragment: aws
'''


EXAMPLES = '''
# Create a new Lightsail instance, register the instance details
- lightsail:
    state: present
    name: myinstance
    region: us-east-1
    zone: us-east-1a
    blueprint_id: ubuntu_16_04
    bundle_id: nano_1_0
    key_pair_name: id_rsa
    user_data: " echo 'hello world' > /home/ubuntu/test.txt"
    wait_timeout: 500
  register: my_instance

- debug:
    msg: "Name is {{ my_instance.instance.name }}"

- debug:
    msg: "IP is {{ my_instance.instance.publicIpAddress }}"

# Delete an instance if present
- lightsail:
    state: absent
    region: us-east-1
    name: myinstance

'''

RETURN = '''
changed:
  description: if a snapshot has been modified/created
  returned: always
  type: bool
  sample:
    changed: true
instance:
  description: instance data
  returned: always
  type: dict
  sample:
    arn: "arn:aws:lightsail:us-east-1:448830907657:Instance/1fef0175-d6c8-480e-84fa-214f969cda87"
    blueprint_id: "ubuntu_16_04"
    blueprint_name: "Ubuntu"
    bundle_id: "nano_1_0"
    created_at: "2017-03-27T08:38:59.714000-04:00"
    hardware:
      cpu_count: 1
      ram_size_in_gb: 0.5
    is_static_ip: false
    location:
      availability_zone: "us-east-1a"
      region_name: "us-east-1"
    name: "my_instance"
    networking:
      monthly_transfer:
        gb_per_month_allocated: 1024
      ports:
        - access_direction: "inbound"
          access_from: "Anywhere (0.0.0.0/0)"
          access_type: "public"
          common_name: ""
          from_port: 80
          protocol: tcp
          to_port: 80
        - access_direction: "inbound"
          access_from: "Anywhere (0.0.0.0/0)"
          access_type: "public"
          common_name: ""
          from_port: 22
          protocol: tcp
          to_port: 22
    private_ip_address: "172.26.8.14"
    public_ip_address: "34.207.152.202"
    resource_type: "Instance"
    ssh_key_name: "keypair"
    state:
      code: 16
      name: running
    support_code: "588307843083/i-0997c97831ee21e33"
    username: "ubuntu"
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


def import_keypair(module, client):
    """
    docstring
    """
    # Check if the keypair already exists

    changed = False

    key_pair_name = module.params.get('key_pair_name')
    public_key = module.params.get('public_key_base64')

    _ch, _kp_name = get_keypair(module, client)

    if _kp_name is not None:
        if _kp_name['name'] == key_pair_name:
            module.fail_json(msg='Keypair with name {0} already exists'.format(key_pair_name))
            return (changed, _kp_name)
    else:
        resp = None
        try:
            resp = client.import_key_pair(keyPairName=key_pair_name, publicKeyBase64=public_key)
            changed = True
        except botocore.exceptions.ClientError as e:
            module.fail_json(msg='Unable to import keypair {0}, error {1}'.format(key_pair_name, e))
        
        return (changed, resp)

def create_keypair(module, client):
    """
    docstring
    """
    # Check if the keypair already exists

    changed = False

    key_pair_name = module.params.get('key_pair_name')

    resp = None

    try:
        resp = client.create_key_pair(keyPairName=key_pair_name)
        changed = True
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg='Unable to create keypair {0}, error {1}'.format(key_pair_name, e))
    
    return (changed, resp)

def delete_key_pair(module, client):
    """
    docstring
    """
    # Check if the keypair already exists

    changed = False

    key_pair_name = module.params.get('key_pair_name')

    resp = None

    try:
        resp = client.create_key_pair(keyPairName=key_pair_name)['operation']
        changed = True
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg='Unable to delete keypair {0}, error {1}'.format(key_pair_name, e))
    

    return (changed, resp)

def get_keypair(module, client):
    """
    docstring
    """
    # Check if the keypair already exists

    changed = False

    key_pair_name = module.params.get('key_pair_name')

    resp = None

    try:
        resp = client.get_key_pair(keyPairName=key_pair_name)['keyPair']
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg='Unable to get keypair {0}, error {1}'.format(key_pair_name, e))

    return (changed, resp)

def get_keypairs(module, client):
    """
    docstring
    """
    # Check if the keypair already exists

    changed = False

    page_token = module.params.get('page_token')

    resp = None

    try:
        resp = client.get_key_pairs(pageToken=page_token)['keyPairs']
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg='Unable to get keypair {0}, error {1}'.format(page_token, e))

    return (changed, resp)

def core(module):
    """
    docstring
    """
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
    response_dict = None
    state = module.params['state']

    if state == 'absent':
        changed, response_dict = delete_key_pair(module, client)
        # changed, instance_dict = delete_instance(module, client, name)
    elif state in ('running', 'stopped'):
        print "foo"
        # changed, instance_dict = startstop_instance(module, client, name, state)
    elif state == 'restarted':
        print "foo"
        # changed, instance_dict = restart_instance(module, client, name)
    elif state == 'present':
        changed, response_dict = import_keypair(module, client)

    module.exit_json(changed=changed, instance=camel_dict_to_snake_dict(response_dict))

def main():
    """
    docstring
    """
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'stopped', 'running', 'restarted']),
        public_key_base64=dict(type='str'),
        key_pair_name=dict(type='str'),
        page=dict(type='str'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(default=300),
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
