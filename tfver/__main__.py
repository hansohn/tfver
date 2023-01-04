#!/usr/bin/env python3

import copy
import json
import re
import sys
from typing import Any, Dict, List, Union

import click
import requests
import semver
import yaml
from packaging.version import parse

from .utils.common import get_platform

TERRAFORM_RELEASES = "https://releases.hashicorp.com/terraform/index.json"


def is_major(version: str) -> bool:
    """
    Tests whether version is formatted as a single integer value.
    Example if version == 1, return true
    """
    test = version.count(".") == 0
    return test


def is_minor(version: str) -> bool:
    """
    Tests whether version is formatted as a major minor integer value.
    Example if version == 1.1, return true
    """
    test = version.count(".") == 1
    return test


def max_version(versions: List[str]) -> str:
    """
    Parse list of symantec versions and return the latest
    """
    return str(max(map(semver.VersionInfo.parse, versions)))


def extend_versions(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingests dict of versions and extends version objects to include latest major
    release as M and latest minor releases as M.m. This fuctionality is the basis
    for supporting extended version queries. Returns recompiled dict of versions
    and associated version metadata.
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


def generate_tags(
    data: Dict[str, Any],
    incl_major: bool = False,
    incl_minor: bool = False,
    template: str = "{tag}",
) -> Dict[str, Any]:
    """
    Populates dict with tags key and associated values. Formats tags based on
    template arguement.
    """
    fmt = lambda tag: template.format(tag=tag)
    for key, val in data.items():
        # include verification
        if is_major(key) and not incl_major:
            continue
        if is_minor(key) and not incl_minor:
            continue
        # tagging
        if i := val.get("tags", None):
            data[key]["tags"] = list(set(i + [fmt(key)]))
        elif is_major(key):
            tags = [fmt(key)]
            if incl_minor:
                version = val["version"]
                mmp = version.split(".")
                maj_min = ".".join(mmp[0:2])
                tags.append(fmt(maj_min))
            data[key].update({"tags": tags})
        else:
            data[key].update({"tags": [fmt(key)]})
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
    "-t",
    "--tag-template",
    type=str,
    help=(
        "Format tags to templatized string. String template must include '{tag}' "
        "keyword which will be replaced with actual tag value during formatting. "
        "example: 'foo/bar:{tag}-dev'"
    ),
)
@click.option(
    "-o",
    "--output",
    default="json",
    show_default=True,
    type=click.Choice(["tfget", "text", "json", "yaml"], case_sensitive=False),
    help="The formatting style for command output.",
)
@click.option(
    "-L",
    "--vlist",
    is_flag=True,
    help="Reformats 'versions' key to list of dicts. Defaults to key/value version dicts.",
)
@click.option(
    "-M",
    "--major",
    is_flag=True,
    help=(
        "Includes major version tag in metadata of all lastest major version releases. "
        "example: 1.2.3 -> 1"
    ),
)
@click.option(
    "-m",
    "--minor",
    is_flag=True,
    help=(
        "Includes minor version tag in metadata of all lastest minor version releases. "
        "example: 1.2.3 -> 1.2"
    ),
)
@click.option("-p", "--prerelease", is_flag=True, help="Include pre-release versions in response.")
@click.option("-v", "--verbose", is_flag=True, help="Include all release metadata in response.")
@click.option(
    "-V",
    "--verboseb",
    is_flag=True,
    help="Include all release metadata and all builds in response.",
)
@click.version_option()
def main(
    build: Union[str, None] = None,
    count: int = 1,
    major: bool = False,
    minor: bool = False,
    output: str = "json",
    prerelease: bool = False,
    regex: Union[str, None] = None,
    tag_template: Union[str, None] = "{tag}",
    url: str = TERRAFORM_RELEASES,
    verbose: bool = False,
    verboseb: bool = False,
    vlist: bool = False,
):
    """
    Gathers a historical list of Terraform versions and their metadata. Produces
    a filtered response based on arguement inputs.
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
    tag_template = tag_template if tag_template and "{tag}" in tag_template else "{tag}"
    data.update({"versions": generate_tags(data["versions"], major, minor, tag_template)})

    # sort versions
    data.update({"versions": sort_dict(data=data["versions"])})

    # compute latest tag
    mmp_versions = filter_list(data=data["versions"].keys(), pattern=r"^v?\d+\.\d+\.\d+$")
    latest_mmp = max_version(mmp_versions)
    data["versions"][latest_mmp]["tags"] += [tag_template.format(tag="latest")]

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
        else:
            click.echo(f"==> Error: unsupported build filter format: '{build}'")
            sys.exit(1)
        release_data.update(
            {"versions": filter_builds(data=data["versions"], build_filter=build_filter)}
        )

    # convert versions to list of dicts
    if vlist:
        versions = list(meta for _, meta in release_data["versions"].items())
        release_data.update({"versions": versions})

    # set single version response to string
    if len(release_vers) == 1:
        if not verbose and not verboseb:
            output = "text"
        release_vers = release_vers[0]

    # determine response type
    response = release_data if verbose or verboseb else release_vers

    # format response for output
    if output.lower() == "tfget":
        click.echo(",".join(release_vers))
    elif output.lower() == "text":
        click.echo(response)
    elif output.lower() == "yaml":
        click.echo(yaml.dump(response, indent=4, sort_keys=True))
    else:
        click.echo(json.dumps(response, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
