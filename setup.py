#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup


def do_setup():
    setup_kwargs = {}
    setup(
        **setup_kwargs,
        use_scm_version = {
            "write_to": "tfrelease/version.py",
            "write_to_template": "__version__ = \"{version}\"",
        }
    )


def main():
    do_setup()


if __name__ == '__main__':
    main()
