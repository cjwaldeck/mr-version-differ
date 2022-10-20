#!/usr/bin/env python3

import requests
import argparse
import subprocess
from pick import pick
import datetime

class DiffRef:
    def __init__(self, head_sha, created_at):
        self.head_sha = head_sha
        self.created_at = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')

    def __repr__(self):
        return f'{self.created_at}, {self.head_sha}'

GITREPO_NAME = '.mr-version-differ'

def make_request(token, request):
    response = requests.get(request, headers={'PRIVATE-TOKEN': token})
    if not response.ok:
        print(f'Request {request} returned error response: {response}')

    return response

def get_api_url(address):
    return f"{address}/api/v4"

def get_details_from_url(url):
    #https://<gitlab-address>/<group>/<project_name>/-/merge_requests/<mr_id>
    #  0   1        2            3          4        5      6            7
    segment_idx_mr_string = 6
    segment_idx_project = 4
    segment_idx_mr_id = 7
    min_len_segments = 8
    url_segments = url.split('/')

    # Sanity check
    if len(url_segments) < min_len_segments \
       or url_segments[segment_idx_mr_string] != 'merge_requests':
        print(f'Invalid url: {url}')
        exit(1)

    # Extract gitlab address
    address_end = url.find('/', len('https://'))
    if (address_end == -1):
        print(f"Corrupt url {url}")
        exit(1)
    address = url[:address_end]

    return address, url_segments[segment_idx_project], url_segments[segment_idx_mr_id]

def get_mr_details(token, url):
    address, project_name, mr_id = get_details_from_url(url)

    # Find project by name
    request = f'{get_api_url(address)}/search?scope=projects&search={project_name}'
    response = make_request(token, request)
    if not response.ok:
        exit(1)

    projects = response.json()
    project = None

    for p in projects:
        if p.get('name') == project_name:
            project = p
            break

    if not project:
        print(f'Could not find project {project_name}.')
        exit(1)

    # Get versions of specified merge request
    request = f"{get_api_url(address)}/projects/{project['id']}/merge_requests/{mr_id}/versions"
    response = make_request(token, request)
    if response.status_code == 404:
        print(f'Could not find specified mr {mr_id}')
        exit(1)
    elif not response.ok:
        exit(1)

    mr_versions = response.json()

    return project, mr_versions

def generate_diff(project, ref_a, ref_b):
    # Initialize a repo if not already exist and add remote
    subprocess.call(['git', 'init', GITREPO_NAME])

    # Will generate error if already exists. Let it for now...
    subprocess.call(['git', '-C', GITREPO_NAME, 'remote', 'add',
                     project['name'], project['ssh_url_to_repo']])

    # Need to fetch refs explicitly as they are not part of any ref group
    subprocess.call(['git', '-C', GITREPO_NAME, 'fetch',
                     project['name'], ref_a.head_sha, ref_b.head_sha])

    # Do not store output as it will loose color information.
    # Let it be outputted to stdout undisturbed
    subprocess.call(['git', '-C', GITREPO_NAME, 'range-diff',
                     f'{ref_b.head_sha}...{ref_a.head_sha}'])

def main():
    parser = argparse.ArgumentParser(description='Range-diff GitLab merge requests.')
    parser.add_argument('--token', required=True, help='Gitlab API token with read_api rights' \
                                                       ' -- generate in profile menu.')
    parser.add_argument('--url', required=True, help='Merge request url')

    args = parser.parse_args()

    project, mr_versions = get_mr_details(args.token, args.url)

    # Prompt user to select two refs
    diff_refs = [DiffRef(v['head_commit_sha'], v['created_at']) for v in mr_versions]
    ref_a, _ = pick(diff_refs, 'Diff from (latest first):')
    diff_refs.remove(ref_a)
    ref_b, _ = pick(diff_refs, 'Diff to:')

    # Generate diff. It will be visible in stdout
    generate_diff(project, ref_a, ref_b)

if __name__ == '__main__':
    main()
