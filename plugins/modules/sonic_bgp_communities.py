#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020 Dell Inc. or its subsidiaries. All Rights Reserved
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

#############################################
#                WARNING                    #
#############################################
#
# This file is auto generated by the resource
#   module builder playbook.
#
# Do not edit this file manually.
#
# Changes to this file will be over written
#   by the resource module builder.
#
# Changes should be made in the model used to
#   generate this file or in the resource module
#   builder template.
#
#############################################

"""
The module file for sonic_bgp_communities
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: sonic_bgp_communities
version_added: 1.0.0
short_description: Configures 'community' settings for a BGP on Enterprise SONiC.
description:
  - This module provides configuration management of BGP bgp_communities for device
    running Enterprise SONiC Distribution by Dell Technologies.
author: "Kumaraguru Narayanan (@nkumaraguru)"
options:
  config:
    description: A list of 'bgp_communities' configurations.
    type: list
    elements: dict
    suboptions:
      name:
        required: True
        type: str
        description:
        - Name of BGP communty list name.
      type:
        type: str
        description:
        - Whether it is a standard or expanded community-list entry.
        required: False
        choices:
        - standard
        - expanded
        default: standard
      permit:
        required: False
        type: bool
        description:
        - Permits or denies this community.
      aann:
        required: False
        type: str
        description:
        - Community number aa:nn format 0..65535:0..65535; applicable for standard BGP community type.
      local_as:
        required: False
        type: bool
        description:
        - Do not send outside local AS (well-known community); applicable for standard BGP community type.
      no_advertise:
        required: False
        type: bool
        description:
        - Do not advertise to any peer (well-known community); applicable for standard BGP community type.
      no_export:
        required: False
        type: bool
        description:
        - Do not export to next AS (well-known community); applicable for standard BGP community type.
      no_peer:
        required: False
        type: bool
        description:
        - Do not export to next AS (well-known community); applicable for standard BGP community type.
      members:
        required: False
        type: dict
        suboptions:
          regex:
            type: list
            elements: str
            required: False
            description:
              - Members of this BGP community list. Regular expression string can be given here. Applicable for expanded BGP community type.
        description:
        - Members of this BGP community list.
      match:
        required: False
        type: str
        description:
        - Matches any/all of the members.
        choices:
        - ALL
        - ANY
        default: ANY
  state:
    description:
    - The state of the configuration after module completion.
    type: str
    choices:
    - merged
    - deleted
    default: merged
"""
EXAMPLES = """
# Using deleted

# Before state:
# -------------
#
# show bgp community-list
# Standard community list test:  match: ANY
#     101
#     201
# Standard community list test1:  match: ANY
#     301

- name: Deletes BGP community member.
  sonic_bgp_communities:
    config:
      - name: test
        members:
          regex:
          - 201
    state: deleted

# After state:
# ------------
#
# show bgp community-list
# Standard community list test:  match: ANY
#     101
# Standard community list test1:  match: ANY
#     301


# Using deleted

# Before state:
# -------------
#
# show bgp community-list
# Standard community list test:  match: ANY
#     101
# Expanded community list test1:   match: ANY
#     201

- name: Deletes a single BGP community.
  sonic_bgp_communities:
    config:
      - name: test
        members:
    state: deleted

# After state:
# ------------
#
# show bgp community-list
# Expanded community list test1:   match: ANY
#     201


# Using deleted

# Before state:
# -------------
#
# show bgp community-list
# Standard community list test:  match: ANY
#     101
# Expanded community list test1:   match: ANY
#     201

- name: Delete All BGP communities.
  sonic_bgp_communities:
    config:
    state: deleted

# After state:
# ------------
#
# show bgp community-list
#


# Using deleted

# Before state:
# -------------
#
# show bgp community-list
# Standard community list test:  match: ANY
#     101
# Expanded community list test1:   match: ANY
#     201

- name: Deletes all members in a single BGP community.
  sonic_bgp_communities:
    config:
      - name: test
        members:
          regex:
    state: deleted

# After state:
# ------------
#
# show bgp community-list
# Expanded community list test:   match: ANY
# Expanded community list test1:   match: ANY
#     201


# Using merged

# Before state:
# -------------
#
# show bgp as-path-access-list
# AS path list test:

- name: Adds 909.* to test as-path list.
  sonic_bgp_as_paths:
    config:
      - name: test
        members:
        - 909.*
    state: merged

# After state:
# ------------
#
# show bgp as-path-access-list
# AS path list test:
#   members: 909.*


"""
RETURN = """
before:
  description: The configuration prior to the model invocation.
  returned: always
  type: list
  sample: >
    The configuration returned will always be in the same format
     of the parameters above.
after:
  description: The resulting configuration model invocation.
  returned: when changed
  type: list
  sample: >
    The configuration returned will always be in the same format
     of the parameters above.
commands:
  description: The set of commands pushed to the remote device.
  returned: always
  type: list
  sample: ['command 1', 'command 2', 'command 3']
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.dellemc.sonic.plugins.module_utils.network.sonic.argspec.bgp_communities.bgp_communities import Bgp_communitiesArgs
from ansible_collections.dellemc.sonic.plugins.module_utils.network.sonic.config.bgp_communities.bgp_communities import Bgp_communities


def main():
    """
    Main entry point for module execution

    :returns: the result form module invocation
    """
    module = AnsibleModule(argument_spec=Bgp_communitiesArgs.argument_spec,
                           supports_check_mode=True)

    result = Bgp_communities(module).execute_module()
    module.exit_json(**result)


if __name__ == '__main__':
    main()
