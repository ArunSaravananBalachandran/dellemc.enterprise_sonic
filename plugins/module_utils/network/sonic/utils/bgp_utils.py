#
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The sonic bgp fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re
from copy import deepcopy

from ansible_collections.ansible.netcommon.plugins.module_utils.network.common import (
    utils,
)
from ansible_collections.dellemc.sonic.plugins.module_utils.network.sonic.utils.utils import (
    normalize_interface_name,
)
from ansible_collections.dellemc.sonic.plugins.module_utils.network.sonic.argspec.bgp.bgp import BgpArgs
from ansible_collections.dellemc.sonic.plugins.module_utils.network.sonic.sonic import send_requests


afi_safi_types_map = {
    'openconfig-bgp-types:IPV4_UNICAST': 'ipv4_unicast',
    'openconfig-bgp-types:IPV6_UNICAST': 'ipv6_unicast',
    'openconfig-bgp-types:L2VPN_EVPN': 'l2vpn_evpn',
}
GET = "get"
network_instance_path = '/data/openconfig-network-instance:network-instances/network-instance'
protocol_bgp_path = 'protocols/protocol=BGP,bgp/bgp'


def get_all_vrfs(module):
    """Get all VRF configurations available in chassis"""
    all_vrfs = []
    ret = []
    request = {"path": "data/sonic-vrf:sonic-vrf/VRF/VRF_LIST", "method": GET}
    try:
        response = send_requests(module, requests=request)
    except ConnectionError as exc:
        module.fail_json(msg=str(exc), code=exc.code)

    if 'sonic-vrf:VRF_LIST' in response[0][1]:
        all_vrf_data = response[0][1].get('sonic-vrf:VRF_LIST', [])
        if all_vrf_data:
            for vrf_data in all_vrf_data:
                all_vrfs.append(vrf_data['vrf_name'])

    return all_vrfs


def get_peergroups(module, vrf_name):
    peer_groups = []
    request_path = '%s=%s/protocols/protocol=BGP,bgp/bgp/peer-groups' % (network_instance_path, vrf_name)
    request = {"path": request_path, "method": GET}
    try:
        response = send_requests(module, requests=request)
    except ConnectionError as exc:
        module.fail_json(msg=str(exc), code=exc.code)

    resp = response[0][1]
    if 'openconfig-network-instance:peer-groups' in resp:
        data = resp['openconfig-network-instance:peer-groups']
        if 'peer-group' in data:
            for peer_group in data['peer-group']:
                pg = {}
                if 'config' in peer_group and 'peer-group-name' in peer_group['config']:
                    pg.update({'name': peer_group['config']['peer-group-name']})
                if 'openconfig-bfd:enable-bfd' in peer_group and 'config' in peer_group['openconfig-bfd:enable-bfd']:
                    if 'enabled' in peer_group['openconfig-bfd:enable-bfd']['config']:
                        pg.update({'bfd': peer_group['openconfig-bfd:enable-bfd']['config']['enabled']})
                if 'timers' in peer_group and 'config' in peer_group['timers']:
                    if 'minimum-advertisement-interval' in peer_group['timers']['config']:
                        pg.update({'advertisement_interval': peer_group['timers']['config']['minimum-advertisement-interval']})
                timers = {}
                if 'timers' in peer_group and 'config' in peer_group['timers']:
                    if 'hold-time' in peer_group['timers']['config']:
                        timers.update({'holdtime': peer_group['timers']['config']['hold-time']})
                if 'timers' in peer_group and 'config' in peer_group['timers']:
                    if 'keepalive-interval' in peer_group['timers']['config']:
                        timers.update({'keepalive': peer_group['timers']['config']['keepalive-interval']})
                capability = {}
                if 'config' in peer_group and 'openconfig-bgp-ext:capability-dynamic' in peer_group['config']:
                    capability.update({'dynamic': peer_group['config']['openconfig-bgp-ext:capability-dynamic']})
                if 'config' in peer_group and 'openconfig-bgp-ext:capability-extended-nexthop' in peer_group['config']:
                    capability.update({'extended_nexthop': peer_group['config']['openconfig-bgp-ext:capability-extended-nexthop']})
                remote_as = {}
                if 'config' in peer_group and 'peer-as' in peer_group['config']:
                    remote_as.update({'peer_as': peer_group['config']['peer-as']})
                if 'config' in peer_group and 'peer-type' in peer_group['config']:
                    remote_as.update({'peer_type': peer_group['config']['peer-type'].lower()})
                if timers:
                    pg.update({'timers': timers})
                if capability:
                    pg.update({'capability': capability})
                if remote_as:
                    pg.update({'remote_as': remote_as})
                peer_groups.append(pg)

    return peer_groups


def get_all_bgp_af_redistribute(module, vrfs, af_redis_params_map):
    """Get all BGP Global Address Family Redistribute configurations available in chassis"""
    all_af_redis_data = []
    ret_redis_data = []
    for vrf_name in vrfs:
        af_redis_data = {}
        request_path = '%s=%s/table-connections' % (network_instance_path, vrf_name)
        request = {"path": request_path, "method": GET}
        try:
            response = send_requests(module, requests=request)
        except ConnectionError as exc:
            module.fail_json(msg=str(exc), code=exc.code)

        if "openconfig-network-instance:table-connections" in response[0][1]:
            af_redis_data.update({vrf_name: response[0][1]['openconfig-network-instance:table-connections']})

        if af_redis_data:
            all_af_redis_data.append(af_redis_data)

    if all_af_redis_data:
        for vrf_name in vrfs:
            key = vrf_name
            val = next((af_redis_data for af_redis_data in all_af_redis_data if vrf_name in af_redis_data), None)
            if not val:
                continue

            val = val[vrf_name]
            redis_data = val.get('table-connection', [])
            if not redis_data:
                continue
            filtered_redis_data = []
            for e_cfg in redis_data:
                af_redis_data = get_from_params_map(af_redis_params_map, e_cfg)
                if af_redis_data:
                    filtered_redis_data.append(af_redis_data)

            if filtered_redis_data:
                ret_redis_data.append({key: filtered_redis_data})

    return ret_redis_data


def get_all_bgp_globals(module, vrfs):
    """Get all BGP configurations available in chassis"""
    all_bgp_globals = []
    for vrf_name in vrfs:
        get_path = '%s=%s/%s/global' % (network_instance_path, vrf_name, protocol_bgp_path)
        request = {"path": get_path, "method": GET}
        try:
            response = send_requests(module, requests=request)
        except ConnectionError as exc:
            module.fail_json(msg=str(exc), code=exc.code)
        for resp in response:
            if "openconfig-network-instance:global" in resp[1]:
                bgp_data = {'global': resp[1].get("openconfig-network-instance:global", {})}
                bgp_data.update({'vrf_name': vrf_name})
                all_bgp_globals.append(bgp_data)
    return all_bgp_globals


def get_bgp_global_af_data(data, af_params_map):
    ret_af_data = {}
    for key, val in data.items():
        if key == 'global':
            if 'afi-safis' in val and 'afi-safi' in val['afi-safis']:
                global_af_data = []
                raw_af_data = val['afi-safis']['afi-safi']
                for each_af_data in raw_af_data:
                    af_data = get_from_params_map(af_params_map, each_af_data)
                    if af_data:
                        global_af_data.append(af_data)
                ret_af_data.update({'address_family': global_af_data})
            if 'config' in val and 'as' in val['config']:
                as_val = val['config']['as']
                ret_af_data.update({'bgp_as': as_val})
        if key == 'vrf_name':
            ret_af_data.update({'vrf_name': val})
    return ret_af_data


def get_bgp_global_data(data, global_params_map):
    bgp_data = {}
    for key, val in data.items():
        if key == 'global':
            global_data = get_from_params_map(global_params_map, val)
            bgp_data.update(global_data)
        if key == 'vrf_name':
            bgp_data.update({'vrf_name': val})
    return bgp_data


def get_from_params_map(params_map, data):
    ret_data = {}
    for want_key, config_key in params_map.items():
        tmp_data = {}
        for key, val in data.items():
            if key == 'config':
                for k, v in val.items():
                    if k == config_key:
                        val_data = val[config_key]
                        ret_data.update({want_key: val_data})
                        if config_key == 'afi-safi-name':
                            ret_data.pop(want_key)
                            for type_k, type_val in afi_safi_types_map.items():
                                if type_k == val_data:
                                    afi_safi = type_val.split('_')
                                    val_data = afi_safi[0]
                                    ret_data.update({'safi': afi_safi[1]})
                                    ret_data.update({want_key: val_data})
                                    break
            else:
                if key == 'timers' and ('config' in val or 'state' in val):
                    tmp = {}
                    if key in ret_data:
                        tmp = ret_data[key]
                    cfg = val['config'] if 'config' in val else val['state']
                    for k, v in cfg.items():
                        if k == config_key:
                            if k != 'minimum-advertisement-interval':
                                tmp.update({want_key: cfg[config_key]})
                            else:
                                ret_data.update({want_key: cfg[config_key]})
                    if tmp:
                        ret_data.update({key: tmp})

                elif isinstance(config_key, list):
                    i = 0
                    if key == config_key[0]:
                        if key == 'afi-safi':
                            cfg_data = config_key[1]
                            for itm in afi_safi_types_map:
                                if cfg_data in itm:
                                    afi_safi = itm[cfg_data].split('_')
                                    cfg_data = afi_safi[0]
                                    ret_data.update({'safi': afi_safi[1]})
                                    ret_data.update({want_key: cfg_data})
                                    break
                        else:
                            cfg_data = {key: val}
                            for cfg_key in config_key:
                                if cfg_key == 'config':
                                    continue
                                new_data = None

                                if cfg_key in cfg_data:
                                    new_data = cfg_data[cfg_key]
                                elif isinstance(cfg_data, dict) and 'config' in cfg_data:
                                    if cfg_key in cfg_data['config']:
                                        new_data = cfg_data['config'][cfg_key]

                                if new_data is not None:
                                    cfg_data = new_data
                                else:
                                    break
                            else:
                                ret_data.update({want_key: cfg_data})
                else:
                    if key == config_key and val:
                        if config_key != 'afi-safi-name' and config_key != 'timers':
                            cfg_data = val
                            ret_data.update({want_key: cfg_data})

    return ret_data


def get_bgp_data(module, global_params_map):
    vrf_list = get_all_vrfs(module)
    data = get_all_bgp_globals(module, vrf_list)

    objs = []
    # operate on a collection of resource x
    for conf in data:
        if conf:
            obj = get_bgp_global_data(conf, global_params_map)
            if obj:
                objs.append(obj)
    return objs


def get_bgp_af_data(module, af_params_map):
    vrf_list = get_all_vrfs(module)
    data = get_all_bgp_globals(module, vrf_list)

    objs = []
    # operate on a collection of resource x
    for conf in data:
        if conf:
            obj = get_bgp_global_af_data(conf, af_params_map)
            if obj:
                objs.append(obj)

    return objs


def get_bgp_as(module, vrf_name):
    as_val = None
    get_path = '%s=%s/%s/global/config' % (network_instance_path, vrf_name, protocol_bgp_path)
    request = {"path": get_path, "method": GET}
    try:
        response = send_requests(module, requests=request)
    except ConnectionError as exc:
        module.fail_json(msg=str(exc), code=exc.code)

    resp = response[0][1]
    if "openconfig-network-instance:config" in resp and 'as' in resp['openconfig-network-instance:config']:
        as_val = resp['openconfig-network-instance:config']['as']
    return as_val


def get_bgp_neighbors(module, vrf_name):
    neighbors_data = None
    get_path = '%s=%s/%s/neighbors' % (network_instance_path, vrf_name, protocol_bgp_path)
    request = {"path": get_path, "method": GET}
    try:
        response = send_requests(module, requests=request)
    except ConnectionError as exc:
        module.fail_json(msg=str(exc), code=exc.code)

    resp = response[0][1]
    if "openconfig-network-instance:neighbors" in resp:
        neighbors_data = resp['openconfig-network-instance:neighbors']

    return neighbors_data


def get_all_bgp_neighbors(module):
    vrf_list = get_all_vrfs(module)
    """Get all BGP neighbor configurations available in chassis"""
    all_bgp_neighbors = []

    for vrf_name in vrf_list:
        neighbors_cfg = {}

        bgp_as = get_bgp_as(module, vrf_name)
        if bgp_as:
            neighbors_cfg['bgp_as'] = bgp_as
            neighbors_cfg['vrf_name'] = vrf_name
        else:
            continue

        neighbors = get_bgp_neighbors(module, vrf_name)
        if neighbors:
            neighbors_cfg['neighbors'] = neighbors

        if neighbors_cfg:
            all_bgp_neighbors.append(neighbors_cfg)

    return all_bgp_neighbors


def get_undefined_bgps(want, have, check_neighbors=None):
    if check_neighbors is None:
        check_neighbors = False

    undefined_resources = []

    if not want:
        return undefined_resources

    if not have:
        have = []

    for want_conf in want:
        undefined = {}
        want_bgp_as = want_conf['bgp_as']
        want_vrf = want_conf['vrf_name']
        have_conf = next((conf for conf in have if (want_bgp_as == conf['bgp_as'] and want_vrf == conf['vrf_name'])), None)
        if not have_conf:
            undefined['bgp_as'] = want_bgp_as
            undefined['vrf_name'] = want_vrf
            undefined_resources.append(undefined)
        if check_neighbors and have_conf:
            want_neighbors = want_conf.get('neighbors', [])
            have_neighbors = have_conf.get('neighbors', [])
            undefined_neighbors = get_undefined_neighbors(want_neighbors, have_neighbors)
            if undefined_neighbors:
                undefined['bgp_as'] = want_bgp_as
                undefined['vrf_name'] = want_vrf
                undefined['neighbors'] = undefined_neighbors
                undefined_resources.append(undefined)

    return undefined_resources


def get_undefined_neighbors(want, have):
    undefined_neighbors = []
    if not want:
        return undefined_neighbors

    if not have:
        have = []

    for want_neighbor in want:
        want_neighbor_val = want_neighbor['neighbor']
        have_neighbor = next((conf for conf in have if want_neighbor_val == conf['neighbor']), None)
        if not have_neighbor:
            undefined_neighbors.append({'neighbor': want_neighbor_val})

    return undefined_neighbors


def validate_bgps(module, want, have):
    validate_bgp_resources(module, want, have)


def validate_bgp_neighbors(module, want, have):
    validate_bgp_resources(module, want, have, check_neighbors=True)


def validate_bgp_resources(module, want, have, check_neighbors=None):
    undefined_resources = get_undefined_bgps(want, have, check_neighbors)
    if undefined_resources:
        err = "Resource not found! {res}".format(res=undefined_resources)
        module.fail_json(msg=err, code=404)


def normalize_neighbors_interface_name(want):
    if want:
        for conf in want:
            neighbors = conf.get('neighbors', None)
            if neighbors:
                normalize_interface_name(neighbors, 'neighbor')
