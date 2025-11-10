import time

from urllib.parse import urlparse

from jenkinsctl.configs.session import Session

def _remove_base_url(url: str):
    return urlparse(url).path

def _get(session: Session, url: str):
    url = _remove_base_url(url)
    url = f"{url}api/json"
    return session.get(url).json()


def build_job(session: Session, job_name: str, params: dict):
    response = None
    if len(params) == 0:
        url = f"/job/{job_name}/build"
        response = session.post(url)
    else:
        url = f"/job/{job_name}/buildWithParameters"
        response = session.post(url, params=params)

    return response.headers.get("Location")


def get_build_number_from_queue(session: Session, queue_url: str, timeout: int = 60):
    """
    Poll the queue item to get the build number once it starts.

    Args:
        session: Jenkins session
        queue_url: Queue item URL returned from build_job()
        timeout: Maximum time to wait for build to start (default: 60s)

    Returns:
        int: Build number once the build starts

    Raises:
        TimeoutError: If build doesn't start within timeout
    """
    queue_path = _remove_base_url(queue_url)
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            raise TimeoutError(f"Build did not start within {timeout} seconds")

        try:
            queue_item = _get(session, queue_path)

            # Check if build has started
            executable = queue_item.get('executable')
            if executable and 'number' in executable:
                return executable['number']

        except Exception:
            # Queue item might not be available yet, continue polling
            pass

        time.sleep(1)


def get_job(session: Session, job_name: str):
    url = f"/job/{job_name}/"
    return _get(session, url)


def get_jobs(session: Session, folder_name: str):
    if folder_name.strip() == "":
        return _get(session, "")

    url = f"/job/{folder_name}/"
    return _get(session, url)


def get_builds_iter(session: Session, job_json):
    builds = job_json["builds"]
    for build in builds:
        yield _get_build(session, job_json, build["number"])


def _get_build(session: Session, job_json, build_no):
    builds = job_json["builds"]
    build = next((build for build in builds if build["number"] == build_no), None)

    return _get(session, build["url"])


def get_build(session: Session, job_name: str, build_no: int):
    url = f"/job/{job_name}/{build_no}/"
    return _get(session, url)


def wait_for_build(session: Session, job_name: str, build_no: int, timeout: int = 3600, interval: int = 2):
    """
    Wait for a build to reach a terminal state.

    Args:
        session: Jenkins session
        job_name: Name of the job
        build_no: Build number to wait for
        timeout: Maximum time to wait in seconds (default: 3600)
        interval: Polling interval in seconds (default: 2)

    Returns:
        dict: Final build JSON with result

    Raises:
        TimeoutError: If build doesn't complete within timeout
    """
    TERMINAL_STATES = {'SUCCESS', 'FAILURE', 'ABORTED', 'UNSTABLE', 'NOT_BUILT'}

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            raise TimeoutError(f"Build {job_name} #{build_no} did not complete within {timeout} seconds")

        build_json = get_build(session, job_name, build_no)

        # Check if build is complete
        result = build_json.get('result')
        building = build_json.get('building', False)
        in_progress = build_json.get('inProgress', False)

        # Build is complete if result is set and it's not building
        if result in TERMINAL_STATES and not building and not in_progress:
            return build_json

        time.sleep(interval)


def progressive_log(session: Session, job_name: str, build_no: int):
    url = f"/job/{job_name}/{build_no}/logText/progressiveText"
    start_byte = 0
    while True:
        response = session.get(url, params={'start': start_byte})
        text = response.text
        print(text, end="")
        start_byte = int(response.headers.get('X-Text-Size', 0))
        if response.headers.get('X-More-Data') == 'false' or text.strip() == "":
            break
        time.sleep(2)
