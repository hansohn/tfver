<div align="center">
  <h3>tfrelease</h3>
  <p>Terraform tool for fetching release metadata</p>
  <p>
    <!-- Build Status -->
    <a href="https://actions-badge.atrox.dev/hansohn/tfrelease/goto?ref=main">
      <img src="https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fhansohn%2Ftfrelease%2Fbadge%3Fref%3Dmain&style=for-the-badge">
    </a>
    <!-- Github Tag -->
    <a href="https://github.com/hansohn/tfrelease/tags/">
      <img src="https://img.shields.io/github/tag/hansohn/tfrelease.svg?style=for-the-badge">
    </a>
    <!-- License -->
    <a href="https://github.com/hansohn/tfrelease/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/hansohn/tfrelease.svg?style=for-the-badge">
    </a>
    <!-- LinkedIn -->
    <a href="https://linkedin.com/in/ryanhansohn">
      <img src="https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555">
    </a>
  </p>
</div>

### Description

Welcome to the `tfrelease` repo. This Python command line utility fetches Terraform
release metadata, filters releases based on query, generates release tags, and
returns the results in your desired output format [text|json|yaml]. It was built
with CI/CD in mind.

### Usage

#### Commands

```
$ tfrelease --help
Usage: tfrelease [OPTIONS]

  Gathers a historical list of Terraform versions and their metadata. Produces
  a filtered response based on arguement inputs.

Options:
  -c, --count INTEGER            Return latest N number of minor release
                                 versions.  [default: 1]
  -r, --regex TEXT               Filter release versions using regex pattern
                                 matching. example: '^(0.15|1)$'
  -b, --build TEXT               Filter build versions by platform os and
                                 arch. example: 'os=linux,arch=amd64'
  -t, --tag-template TEXT        Format tags to templatized string. String
                                 template must include '{tag}' keyword which
                                 will be replaced with actual tag value during
                                 formatting. example: 'foo/bar:{tag}-dev'
  -o, --output [text|json|yaml]  The formatting style for command output.
                                 [default: json]
  -L, --vlist                    Reformats 'versions' key to list of dicts.
                                 Defaults to key/value version dicts.
  -M, --major                    Includes major version tag in metadata of all
                                 lastest major version releases. example:
                                 1.2.3 -> 1
  -m, --minor                    Includes minor version tag in metadata of all
                                 lastest minor version releases. example:
                                 1.2.3 -> 1.2
  -p, --prerelease               Include pre-release versions in response.
  -v, --verbose                  Include all release metadata in response.
  -V, --verboseb                 Include all release metadata and all builds
                                 in response.
  --version                      Show the version and exit.
  --help                         Show this message and exit.
```

# Makefile

Additionally, a Makefile has been included in this repo to assist with common
development-related functions. I've included the following make targets for
convenience:

```
Available targets:

  build                               Build python package
  clean                               Clean everything
  clean/build                         Clean python build directories
  clean/docker                        Clean docker build images
  clean/venv                          Clean virtual environment directory
  docker                              Docker launch testing environment
  docker/build                        Docker build image
  docker/run                          Docker run image
  help                                Help screen
  help/all                            Display help for all targets
  help/short                          This help short screen
  lint                                Run all linters, validators, and security analyzers
  lint/bandit                         Python security linter
  lint/black                          Python code formatter
  lint/flake8                         Python styleguide enforcement
  lint/mypy                           Python static typing
  lint/pylint                         Python linter
  python/build                        Python build package
  python/packages                     Python install packages from requirements file(s)
  python/venv                         Python configure virtual environment
  upload/check                        Python upload check
  upload/pypi                         Python upload package to pypi
  upload/testpypi                     Python upload package to testpypi
  venv                                Create virtual environment and install requirements
```
