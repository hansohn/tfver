#!/usr/bin/env python3

import copy
import json
import re
from typing import Any, Dict, List, Union

import click
import requests
import semver
import yaml
from packaging.version import parse
from .utils.common import get_platform

TERRAFORM_RELEASES = "https://releases.hashicorp.com/terraform/index.json"


def max_version(versions: List[str]) -> str:
    """
    Parse list of symantec versions and return the latest
    """
    return str(max(map(semver.VersionInfo.parse, versions)))


def extend_versions(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest list of versions and return dict of semver metadata
    """
    modified: Dict[str, Any] = {}
    for key, val in data.items():
        mmp = key.split(".")
        maj = mmp[0]
        maj_min = ".".join(mmp[0:2])
        if i := modified.get(maj, None):
            modified[maj] = data[max_version([i["version"], key])]
            if j := modified.get(maj_min, None):
                modified[maj_min] = data[max_version([j["version"], key])]
            else:
                modified[maj_min] = val
        else:
            modified[maj] = val
            modified[maj_min] = val
        modified[key] = val
    return dict(sorted(modified.items(), key=lambda i: parse(i[0])))


def rename_extended_versions(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rename extended version keys to actual versions
    """
    modified = copy.deepcopy(data)
    pattern = r"^v?\d+(\.\d+)?$"
    regex = re.compile(pattern)
    for key, val in modified.items():
        if regex.match(key):
            version = val["version"]
            data[version] = data.pop(key)
    return data


def filter_builds(data: Dict[str, Any], build_filter: Dict[str, str]) -> Dict[str, Any]:
    """
    Filter build results based on build filter
    """
    for key, val in data.items():
        builds = []
        for build in val.get("builds", []):
            build_platform = {i: build.get(i, None) for i in build_filter.keys()}
            if build_filter == build_platform:
                builds.append(build)
        if len(builds) > 0:
            data[key]["builds"] = builds
    return data


def generate_tags(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    populate dict with tags key and associates tag values
    """
    for key, val in data.items():
        if i := val.get("tags", None):
            data[key]["tags"] = list(set(i + [key]))
        elif "." not in key:
            version = val["version"]
            mmp = version.split(".")
            maj_min = ".".join(mmp[0:2])
            data[key].update({"tags": [key, maj_min]})
        else:
            data[key].update({"tags": [key]})
        data[key]["tags"].sort()
    return data


def filter_list(data: List[str], pattern: str) -> List[str]:
    """
    Filter list using Regex pattern matching
    """
    regex = re.compile(pattern)
    match_elem = lambda i: regex.match(i)
    fltr = filter(match_elem, data)
    return list(fltr)


def filter_dict(data: Dict[str, Any], pattern: str) -> Dict[str, Any]:
    """
    Filter dictionary using Regex pattern matching
    """
    regex = re.compile(pattern)
    match_key = lambda i: regex.match(i[0])
    fltr = filter(match_key, data.items())
    return dict(fltr)


def slice_dict(
    data: Dict[str, Any],
    key: Union[str, None] = None,
    start_index: int = 0,
    stop_index: Union[int, None] = None,
) -> Dict[str, Any]:
    """
    Compile list from dict keys, slice elements from list, filter dict using
    sliced list of elements as key values
    """
    dataset = data.get(key, {}) if key else data
    dataset_keys = list(dataset.keys())
    stop_index = stop_index or len(dataset_keys)
    key_slice = dataset_keys[start_index:stop_index]
    filter_by_key = lambda collection, keys: {i: collection[i] for i in keys}
    output = filter_by_key(dataset, key_slice)
    if key:
        data.update({key: output})
    else:
        data = output
    return data


def sort_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sort dictionary by keys
    """
    parse_key = lambda i: parse(i[0])
    return dict(sorted(data.items(), key=parse_key))


@click.command()
@click.option(
    "-c",
    "--count",
    default=1,
    show_default=True,
    type=int,
    help="Return latest N number of minor release versions.",
)
@click.option(
    "-r",
    "--regex",
    type=str,
    help="Filter release versions using regex pattern matching. example: '^(0.15|1)$'",
)
@click.option(
    "-b",
    "--build",
    type=str,
    help="Filter build versions by platform os and arch. example: 'os=linux,arch=amd64'",
)
@click.option(
    "-o",
    "--output",
    default="json",
    show_default=True,
    type=click.Choice(["text", "json", "yaml"], case_sensitive=False),
    help="The formatting style for command output.",
)
@click.option("-p", "--prerelease", is_flag=True, help="Include pre-release versions in response.")
@click.option("-v", "--verbose", is_flag=True, help="Include all release metadata in response.")
@click.option(
    "-V",
    "--bverbose",
    is_flag=True,
    help="Include all release metadata and all builds in response.",
)
@click.version_option()
def main(
    url: str = TERRAFORM_RELEASES,
    count: int = 1,
    regex: Union[str, None] = None,
    build: Union[str, None] = None,
    output: str = "json",
    prerelease: bool = False,
    verbose: bool = False,
    bverbose: bool = False,
):
    """
    Compute Terraform versions. Return latest n versions as dict with optional
    tag values.
    """

    # create data object from terraform release request
    try:
        req = requests.get(url)
        req.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
    except requests.exceptions.RequestException as err:
        print(err.response.text)
    data = json.loads(req.text)

    # filter out prerelease versions
    if not prerelease:
        data.update(
            {"versions": filter_dict(data=data["versions"], pattern=r"^v?\d+(\.\d+(\.\d+)?)?$")}
        )

    # extend versions
    data.update({"versions": extend_versions(data["versions"])})

    # generate tags
    data.update({"versions": generate_tags(data["versions"])})

    # sort versions
    data.update({"versions": sort_dict(data=data["versions"])})

    # compute latest tag
    mmp_versions = filter_list(data=data["versions"].keys(), pattern=r"^v?\d+\.\d+\.\d+$")
    latest_mmp = max_version(mmp_versions)
    data["versions"][latest_mmp]["tags"] += ["latest"]

    # if regex, filter versions based on regex pattern
    # else return n results from data structure
    if regex:
        data.update({"versions": filter_dict(data=data["versions"], pattern=regex)})
    else:
        start_index = count * -1
        data.update({"versions": filter_dict(data=data["versions"], pattern=r"^v?\d+\.\d+$")})
        latest_n = slice_dict(data=data, key="versions", start_index=start_index)

    # process payload for response
    release_data = data if regex else latest_n
    release_data["versions"].update(rename_extended_versions(release_data["versions"]))
    release_vers = list(release_data["versions"].keys())

    # filter builds
    if build or verbose:
        if build and "=" in build:
            verbose = True
            build_filter = dict([i.split("=") for i in build.split(",")])
        elif verbose:
            build_filter = get_platform()
        data.update({"versions": filter_builds(data=data["versions"], build_filter=build_filter)})

    if len(release_vers) == 1:
        if not verbose and not bverbose:
            output = "text"
        release_vers = release_vers[0]

    response = release_data if verbose or bverbose else release_vers
    if output.lower() == "text":
        click.echo(response)
    elif output.lower() == "yaml":
        click.echo(yaml.dump(response, indent=4, sort_keys=True))
    else:
        click.echo(json.dumps(response, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
