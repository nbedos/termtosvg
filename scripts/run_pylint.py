# until pylint 2.5.0 is released
# https://github.com/PyCQA/pylint/pull/3260/files
# https://github.com/marrink-lab/vermouth-martinize/blob/master/run_pylint.py

# -*- coding: utf-8 -*-
# Copyright 2018 University of Groningen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
from pylint import lint

desc = "PyLint wrapper that add the --fail-under option."\
       " All other arguments are passed to pylint."
parser = argparse.ArgumentParser(description=desc, allow_abbrev=False)
parser.add_argument('--fail-under', dest='threshold', type=float, default=8,
                    help='If the final score is more than THRESHOLD, exit with'
                    ' exitcode 0, and pylint\'s exitcode otherwise.')

args, remaining_args = parser.parse_known_args()

threshold = args.threshold

run = lint.Run(remaining_args, do_exit=False)
score = run.linter.stats['global_note'] # Yes this is a terrible name for the score

if score < threshold:
    sys.exit(run.linter.msg_status)
