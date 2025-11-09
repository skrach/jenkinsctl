import sys
from typing import Optional

from jenkinsctl.configs.session import Session
from jenkinsctl.jenkins.commons import get_last_build_no_if_none
from jenkinsctl.jenkins.job import wait_for_build
from jenkinsctl.jenkins.utils import normalize_job_path
from jenkinsctl.jenkins.console_util import format_timestamp


def wait_handler(session: Session, job_name: str, build_no: Optional[int], timeout: int, interval: int):
    job_name = normalize_job_path(job_name)
    build_no = get_last_build_no_if_none(session, job_name, build_no)

    print(f"Waiting for build {job_name} #{build_no} to complete...")
    print(f"Timeout: {timeout}s, Poll interval: {interval}s")

    try:
        build_json = wait_for_build(session, job_name, build_no, timeout, interval)

        # Display build results
        result = build_json.get('result')
        duration = build_json.get('duration', 0) / 1000  # Convert to seconds
        timestamp = build_json.get('timestamp', 0)

        print(f"\nBuild completed!")
        print(f"Result: {result}")
        print(f"Duration: {duration:.2f}s")
        print(f"Finished at: {format_timestamp(timestamp)}")
        print(f"URL: {build_json.get('url', 'N/A')}")

        # Exit with appropriate code based on result
        if result == 'SUCCESS':
            sys.exit(0)
        elif result in ['FAILURE', 'ABORTED', 'UNSTABLE', 'NOT_BUILT']:
            sys.exit(1)
        else:
            sys.exit(2)  # Unknown result

    except TimeoutError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(3)
