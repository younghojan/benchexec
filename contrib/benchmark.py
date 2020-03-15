#!/usr/bin/env python3

# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) Dirk Beyer
#
# SPDX-License-Identifier: Apache-2.0

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import subprocess
import sys

from benchexec import __version__
import benchexec.benchexec
import benchexec.model
import benchexec.tools
import benchexec.util

sys.dont_write_bytecode = True  # prevent creation of .pyc files

# Add ./benchmark/tools to __path__ of benchexec.tools package
# such that additional tool-wrapper modules can be placed in this directory.
benchexec.tools.__path__ = [
    os.path.join(os.path.dirname(__file__), "benchmark", "tools")
] + benchexec.tools.__path__


class Benchmark(benchexec.benchexec.BenchExec):
    """
    An extension of BenchExec for use with CPAchecker
    to execute benchmarks in the AWS Cloud.
    """

    DEFAULT_OUTPUT_PATH = "test/results/"

    def create_argument_parser(self):
        parser = super(Benchmark, self).create_argument_parser()

        aws_args = parser.add_argument_group("Options for using Amazon AWS Cloud")
        aws_args.add_argument(
            "--aws",
            dest="aws",
            action="store_true",
            help="Use Amazon AWS to execute benchmarks.",
        )
        aws_args.add_argument(
            "--awsToken",
            dest="token",
            metavar="TOKEN",
            type=str,
            help="The token used for the internal post/get http-requests.",
        )

        return parser

    def load_executor(self):
        if self.config.aws:
            if not self.config.token:
                sys.exit("Cannot run aws without a user-specific token")
            import benchmark.aws as executor

            logging.debug(
                "Running benchexec %s using Amazon AWS.", __version__,
            )
        else:
            logging.warning(
                "AWS flag was not specified. Benchexec will be executed only on the local machine."
            )
            executor = super(Benchmark, self).load_executor()

        original_load_function = benchexec.model.load_tool_info

        # The following code block is for testing only and will be removed eventually
        def build_cpachecker_before_load(tool_name, *args, **kwargs):
            if tool_name == "cpachecker":
                # This duplicates the logic from the tool-info module,
                # but it cannot be called here.
                script = benchexec.util.find_executable("cpa.sh", "scripts/cpa.sh")
                base_dir = os.path.join(os.path.dirname(script), os.path.pardir)
                build_file = os.path.join(base_dir, "build.xml")
                if os.path.exists(build_file) and subprocess.call(
                    ["ant", "-q", "jar"], cwd=base_dir, shell=False,
                ):
                    sys.exit("Failed to build CPAchecker, please fix the build first.")

            return original_load_function(tool_name, *args, **kwargs)

        # Monkey-patch BenchExec to build CPAchecker before loading the tool-info
        # module (https://gitlab.com/sosy-lab/software/cpachecker/issues/549)
        benchexec.model.load_tool_info = build_cpachecker_before_load

        return executor


if __name__ == "__main__":
    benchexec.benchexec.main(Benchmark())
