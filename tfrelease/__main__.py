#!/usr/bin/env python3

import copy
import json
import re
import yaml
from typing import Any, Dict, List

import click
import requests
import semver
from packaging.version import parse

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
    data: Dict[str, str], key: str = None, start_index: int = None, stop_index: int = None
) -> Dict[str, str]:
    """
    Compile list from dict keys, slice elements from list, filter dict using
    sliced list of elements as key values
    """
    sample = data.get(key) if key else data
    scope = list(sample.keys())[start_index:stop_index]
    filter_by_key = lambda collection, keys: {i: collection[i] for i in keys}
    output = filter_by_key(sample, scope)
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
@click.option("-c", "--count", default=1, show_default=True, type=int, help="Return latest N number of minor release versions.")
@click.option("-r", "--regex", type=str, help="Filter release versions using regex pattern matching. example: \'^(0.15|1)$\'")
@click.option("-o", "--output", default="json", show_default=True, type=click.Choice(["text", "json", "yaml"], case_sensitive=False), help="The formatting style for command output.")
@click.option("-p", "--prerelease", is_flag=True, help="Include pre-release versions in response.")
@click.option("-v", "--verbose", is_flag=True, help="Include all release metadata in response.")
@click.version_option()
def main(
    url: str = TERRAFORM_RELEASES,
    count: int = 1,
    regex: str = None,
    output: str = "json",
    prerelease: bool = False,
    verbose: bool = False,
) -> str:
    """
    Compute Terraform versions. Return latest n versions as dict with optional tag values
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
    # release_vers = list(release_data["versions"].keys())
    release_vers = list(release_data["versions"].keys())
    if len(release_vers) == 1:
        output = "text"
        release_vers = release_vers[0]

    response = release_data if verbose else release_vers
    if output.lower() =="text":
        click.echo(response)
    elif output.lower() == "yaml":
        click.echo(yaml.dump(response, indent=4, sort_keys=True))
    else:
        click.echo(json.dumps(response, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
