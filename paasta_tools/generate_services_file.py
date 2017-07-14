#!/usr/bin/env python
# Copyright 2015-2016 Yelp Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
A simple script to enumerate all smartstack namespaces and output
a /etc/services compatible file
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import json
import os
import socket
from datetime import datetime

import service_configuration_lib
import yaml

from paasta_tools.marathon_tools import get_all_namespaces
from paasta_tools.marathon_tools import get_all_namespaces_for_service
from paasta_tools.utils import atomic_file_write
from paasta_tools.utils import compose_job_id
from paasta_tools.utils import DEFAULT_SOA_DIR


YOCALHOST = '169.254.255.254'


def parse_args():
    parser = argparse.ArgumentParser(
        description='',
    )
    parser.add_argument('-o', '--output', help="Output filename.", dest='output_filename',
                        required=True)
    parser.add_argument('-f', '--format', help="Output format. Defaults to rfc1700", dest='output_format',
                        choices=['rfc1700', 'yaml', 'json'], default='rfc1700')
    args = parser.parse_args()
    return args


def get_service_lines_for_service(service):
    lines = []
    config = service_configuration_lib.read_service_configuration(service)
    port = config.get('port', None)
    description = config.get('description', "No description")

    if port is not None:
        lines.append("%s\t%d/tcp\t# %s" % (service, port, description))

    for namespace, config in get_all_namespaces_for_service(service, full_name=False):
        proxy_port = config.get('proxy_port', None)
        if proxy_port is not None:
            lines.append("%s\t%d/tcp\t# %s" % (compose_job_id(service, namespace), proxy_port, description))
    return lines


def write_yaml_file(filename):
    previous_config = maybe_load_previous_config(filename, yaml.safe_load)
    configuration = generate_configuration()

    if previous_config and previous_config == configuration:
        return

    with atomic_file_write(filename) as fp:
        fp.write(
            '# This file is automatically generated by paasta_tools.\n'
            '# It was automatically generated at {now} on {host}.\n'.format(
                host=socket.getfqdn(),
                now=datetime.now().isoformat(),
            ),
        )
        yaml.safe_dump(
            configuration,
            fp,
            indent=2,
            explicit_start=True,
            default_flow_style=False,
            allow_unicode=False,
        )


def maybe_load_previous_config(filename, config_loader):
    try:
        with open(filename, 'r') as fp:
            previous_config = config_loader(fp)
            return previous_config
    except Exception:
        pass
    return None


def generate_configuration():
    service_data = get_all_namespaces()
    config = {}
    for (name, data) in service_data:
        proxy_port = data.get('proxy_port')
        if proxy_port is None:
            continue
        config[name] = {
            'host': YOCALHOST,
            'port': int(proxy_port),
        }
    return config


def write_json_file(filename):
    configuration = generate_configuration()
    with atomic_file_write(filename) as fp:
        json.dump(
            obj=configuration,
            fp=fp,
            indent=2,
            sort_keys=True,
            separators=(',', ': '),
        )


def write_rfc1700_file(filename):
    strings = []
    for service in sorted(os.listdir(DEFAULT_SOA_DIR)):
        strings.extend(get_service_lines_for_service(service))
    with atomic_file_write(filename) as fp:
        fp.write("\n".join(strings))


def main():
    args = parse_args()
    if args.output_format == 'rfc1700':
        write_rfc1700_file(filename=args.output_filename)
    elif args.output_format == 'yaml':
        write_yaml_file(filename=args.output_filename)
    elif args.output_format == 'json':
        write_json_file(filename=args.output_filename)
    else:
        raise(NotImplementedError)


if __name__ == "__main__":
    main()
