import sys
from typing import Optional

from jenkinsctl.configs.session import Session
from jenkinsctl.jenkins.commons import get_last_build_no_if_none
from jenkinsctl.jenkins.console_util import format_timestamp
from jenkinsctl.jenkins.job import get_build, build_job, get_build_number_from_queue, wait_for_build
from jenkinsctl.jenkins.utils import get_build_params, normalize_job_path


def rebuild_handler(session: Session, job_name: str, build_no: Optional[int], wait: bool = False, timeout: int = 3600, interval: int = 2):
    job_name = normalize_job_path(job_name)
    build_no = get_last_build_no_if_none(session, job_name, build_no)
    build = get_build(session, job_name, build_no)
    location = build_job(session, job_name, get_build_params(build))
    print(f"Build queued: {location}")

    if wait:
        try:
            # Get build number from queue
            print("Waiting for build to start...")
            new_build_no = get_build_number_from_queue(session, location, timeout=60)
            print(f"Build #{new_build_no} started")

            # Wait for build to complete
            print(f"Waiting for build to complete (timeout: {timeout}s, interval: {interval}s)...")
            build_json = wait_for_build(session, job_name, new_build_no, timeout, interval)

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
