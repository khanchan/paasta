#!/usr/bin/env python
# Copyright 2015-2017 Yelp Inc.
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
paasta_oom_logger is supposed to be used as a syslog-ng destination.
It looks for OOM events in the log, adds PaaSTA service and instance names
and send JSON-encoded messages the Scribe stream 'tmp_paasta_oom_events'.

syslog-ng.conf:

destination paasta_oom_logger {
  program("exec /usr/bin/paasta_oom_logger" template("${UNIXTIME} ${HOST} ${MESSAGE}\n") );
};

filter f_cgroup_oom {
  match("killed as a result of limit of");
};

log {
  source(s_all);
  filter(f_cgroup_oom);
  destination(paasta_oom_logger);
};
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import re
import sys
from collections import namedtuple

from clog.loggers import ScribeLogger
from docker.errors import APIError

from paasta_tools.utils import _log
from paasta_tools.utils import DEFAULT_LOGLEVEL
from paasta_tools.utils import get_docker_client
from paasta_tools.utils import load_system_paasta_config


def capture_oom_events_from_stdin():
    oom_regex = re.compile('^(\d+)\s([a-zA-Z0-9\-]+)\s.*Task in /docker/(\w{12})\w+ killed as a')

    while True:
        syslog = sys.stdin.readline()
        if not syslog:
            break
        r = oom_regex.search(syslog)
        if r:
            yield (int(r.group(1)), r.group(2), r.group(3))


def get_container_env_as_dict(docker_inspect):
    env_vars = {}
    config = docker_inspect.get('Config')
    if config is not None:
        env = config.get('Env', [])
        for i in env:
            name, _, value = i.partition('=')
            env_vars[name] = value
    return env_vars


def log_to_scribe(logger, log_line):
    """Send the event to 'tmp_paasta_oom_events'."""
    line = ('{"timestamp": %d, "hostname": "%s", "container_id": "%s", "cluster": "%s", '
            '"service": "%s", "instance": "%s"}' % (
                log_line.timestamp, log_line.hostname,
                log_line.container_id, log_line.cluster, log_line.service, log_line.instance,
            ))
    logger.log_line('tmp_paasta_oom_events', line)


def log_to_paasta(log_line):
    """Add the event to the standard PaaSTA logging backend."""
    line = ('A process in the container %s on %s killed by OOM.'
            % (log_line.container_id, log_line.hostname))
    _log(
        service=log_line.service, instance=log_line.instance, component='oom',
        cluster=log_line.cluster, level=DEFAULT_LOGLEVEL, line=line,
    )


def main():
    LogLine = namedtuple(
        'LogLine', [
            'timestamp', 'hostname', 'container_id',
            'cluster', 'service', 'instance',
        ],
    )

    scribe_logger = ScribeLogger(host='169.254.255.254', port=1463, retry_interval=5)
    cluster = load_system_paasta_config().get_cluster()
    client = get_docker_client()
    for timestamp, hostname, container_id in capture_oom_events_from_stdin():
        try:
            docker_inspect = client.inspect_container(resource_id=container_id)
        except (APIError):
            continue
        env_vars = get_container_env_as_dict(docker_inspect)
        log_line = LogLine(
            timestamp=timestamp,
            hostname=hostname,
            container_id=container_id,
            cluster=cluster,
            service=env_vars.get('PAASTA_SERVICE', 'unknown'),
            instance=env_vars.get('PAASTA_INSTANCE', 'unknown'),
        )
        log_to_scribe(scribe_logger, log_line)
        log_to_paasta(log_line)


if __name__ == "__main__":
    main()
