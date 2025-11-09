import logging
import sys
from io import TextIOWrapper
from typing import List

import yaml

from jenkinsctl.configs.session import Session
from jenkinsctl.jenkins.console_util import json_preety, format_timestamp
from jenkinsctl.jenkins.job import build_job, get_build_number_from_queue, wait_for_build
from jenkinsctl.jenkins.utils import normalize_job_path

log = logging.getLogger(__name__)


def get_config_from_yaml(file):
    config_data = None
    try:
        with open(file.name, "r") as config_file:
            config_data = yaml.safe_load(config_file)  # Use safe_load for YAML
    except FileNotFoundError:
        print(f"Error: Configuration file '{file}' not found.")
        sys.exit()
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML format in '{file}': {e}")
        sys.exit()

    return config_data


def get_conf(file, params):
    config = get_config_from_yaml(file)
    override_params(params, config)
    return config


def override_params(params, file_config):
    for param in params:
        name, value = param.split('=')
        file_config['params'][name] = value


def build_handler(session: Session, file: TextIOWrapper, params: List[str], wait: bool = False, timeout: int = 3600, interval: int = 2):
    conf = get_conf(file, params)
    log.debug(f"config: {json_preety(conf)}")
    job_name = normalize_job_path(conf["job"])
    location = build_job(session, job_name, conf["params"])
    print(f"Build queued: {location}")

    if wait:
        try:
            # Get build number from queue
            print("Waiting for build to start...")
            build_no = get_build_number_from_queue(session, location, timeout=60)
            print(f"Build #{build_no} started")

            # Wait for build to complete
            print(f"Waiting for build to complete (timeout: {timeout}s, interval: {interval}s)...")
            build_json = wait_for_build(session, job_name, build_no, timeout, interval)

            # Display results
            result = build_json.get('result')
            duration = build_json.get('duration', 0) / 1000
            timestamp = build_json.get('timestamp', 0)

            print(f"\nBuild completed!")
            print(f"Result: {result}")
            print(f"Duration: {duration:.2f}s")
            print(f"Finished at: {format_timestamp(timestamp)}")
            print(f"URL: {build_json.get('url', 'N/A')}")

            # Exit with appropriate code
            if result == 'SUCCESS':
                sys.exit(0)
            elif result in ['FAILURE', 'ABORTED', 'UNSTABLE', 'NOT_BUILT']:
                sys.exit(1)
            else:
                sys.exit(2)

        except TimeoutError as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(3)
