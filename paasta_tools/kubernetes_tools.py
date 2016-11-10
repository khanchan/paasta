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
import logging

import service_configuration_lib

from paasta_tools.long_running_service_tools import LongRunningServiceConfig
from paasta_tools.utils import deep_merge_dictionaries
from paasta_tools.utils import DEFAULT_SOA_DIR
from paasta_tools.utils import get_paasta_branch
from paasta_tools.utils import load_v2_deployments_json
from paasta_tools.utils import NoConfigurationForServiceError


log = logging.getLogger(__name__)


def load_kubernetes_pod_config(service, instance, cluster, load_deployments=True, soa_dir=DEFAULT_SOA_DIR):
    general_config = service_configuration_lib.read_service_configuration(
        service,
        soa_dir=soa_dir
    )
    kubernetes_conf_file = "kubernetes-%s" % cluster
    log.info("Reading kubernetes configuration file: %s.yaml", kubernetes_conf_file)
    instance_configs = service_configuration_lib.read_extra_service_information(
        service_name=service,
        extra_info=kubernetes_conf_file,
        soa_dir=soa_dir
    )

    if instance not in instance_configs:
        raise NoConfigurationForServiceError(
            "%s not found in config file %s/%s/%s.yaml." % (instance, soa_dir, service, kubernetes_conf_file)
        )

    general_config = deep_merge_dictionaries(overrides=instance_configs[instance], defaults=general_config)

    branch_dict = {}
    if load_deployments:
        deployments_json = load_v2_deployments_json(service, soa_dir=soa_dir)
        branch = general_config.get('branch', get_paasta_branch(cluster, instance))
        deploy_group = general_config.get('deploy_group', branch)
        branch_dict = deployments_json.get_branch_dict_v2(service, branch, deploy_group)

    return KubernetesPodConfig(
        service=service,
        cluster=cluster,
        instance=instance,
        config_dict=general_config,
        branch_dict=branch_dict,
    )


class KubernetesPodConfig(LongRunningServiceConfig):

    def __init__(self, service, instance, cluster, config_dict, branch_dict):
        super(KubernetesPodConfig, self).__init__(
            cluster=cluster,
            instance=instance,
            service=service,
            config_dict=config_dict,
            branch_dict=branch_dict,
        )