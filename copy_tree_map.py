#!/usr/bin/env python3

# Copyright 2018 Markus Holmström (MawKKe)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
 Copy directory structure and files, possibly filtering and/or mapping (converting)
 from one format to another.
"""

import argparse
import functools
import os
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count

__author__   = "Markus Holmström (MawKKe)"
__email__    = "markus@mawkke.fi"
__license__  = "Apache 2.0"
__homepage__ = "https://github.com/MawKKe/copy-tree-map"


def ffmpeg_conv(src, dst, codec, bitrate):

    cmd = ["ffmpeg", "-loglevel", "warning", "-i", src, "-c:a", codec, "-b:a", bitrate, "-vn", dst]

    def inner():
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.check_returncode()
            return (True, "")
        except subprocess.CalledProcessError as e:
            return (False, e.stderr.decode('utf8').strip())

    ret, msg = inner()

    return {"success": ret, "src": src, "dst": dst, "cmd": cmd, "msg": msg}


def copyjob(src, dst, *args, **kwargs):
    try:
        shutil.copy2(src, dst, *args, **kwargs)
        msg = None
        ret = True
    except Exception as e:
        ret = False
        msg = str(e)
    return {"success": ret, "src": src, "dst": dst, "cmd": ["shutil.copy2"], "msg": msg}


# pool, mapfuncs are arguments passed via partial application.
# the rest follow the signature of shutil.copy & .copy2
def _mycopy(pool, futures, mapfuncs, src, _dst, *args, verbose=False, **kwargs):

    dst = pathlib.Path(_dst)

    out_params = mapfuncs.get(dst.suffix.lstrip("."), None)

    if out_params is not None:
        out_codec   = out_params["codec"]
        out_ext     = out_params["ext"]
        out_bitrate = out_params["bitrate"]

        # Will crash if no such codec exists. This is intended behaviour
        newdest = str(pathlib.Path(dst).with_suffix("." + out_ext))

        if verbose:
            print(">> [CONV] '{0}' -> '{1}'".format(src, newdest))

        fut = pool.submit(ffmpeg_conv, src, newdest, out_codec, out_bitrate)
        futures.append(fut)
        return newdest

    else:
        if verbose:
            print(">> [COPY] '{0}' -> '{1}'".format(src, dst))
        fut = pool.submit(copyjob, src, dst, *args, **kwargs)
        futures.append(fut)


# e.g 'flac:libmp3lame:ogg:128k' -> ('flac', 'libmp3lam3', '128k')
_PATT = re.compile(r"([a-zA-Z0-9]+):([a-zA-Z0-9]+):([a-zA-Z0-9]+):(\d+k)")


def parse_ffmpeg_rule(rule):
    parsed = _PATT.findall(rule)
    if not parsed:
        return None
    vals = parsed[0]
    return vals[0], {"codec": vals[1], "ext": vals[2], "bitrate": vals[3]}


class FFMPEGRuleAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(FFMPEGRuleAction, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        def _gen():
            for val in values:
                rule = parse_ffmpeg_rule(val)
                if not rule:
                    emsg = "Invalid FFMPEG_RULE rule: '{}' (See --help for details.)"
                    raise argparse.ArgumentError(self, emsg.format(val))
                else:
                    yield rule

        addendum = dict(_gen())
        existing = getattr(namespace, self.dest, None) or {}
        newdict = {**addendum, **existing}  # clever trick for merging two dictionaries
        setattr(namespace, self.dest, newdict)


def parse_args(argv):
    """
    Parse list of strings into argparse.Namespace()

    Arguments:

    argv
        a list of strings, typically contents of sys.argv

    WARNING: if argv is malformed, the process will exit. Avoid using this function in tests.
    """
    description = ("Copy directory structure and files, "
                   "possibly filtering and/or mapping (converting) "
                   "from one format to another.")

    _epilog = \
    """
    ---

    The switch --ffmpeg can be used for converting audio files from one format to another.
    The FFMPEG_RULE expects the following colon-delimited pattern:

        <INPUT-EXTENSION>:<OUTPUT-CODEC>:<OUTPUT-EXTENSION>:<OUTPUT-BITRATE>

    where
        <INPUT-EXTENSION>  Determines which input files this rule matches (by file extension)
        <OUTPUT-CODEC>     Selects the output file audio codec should be.
        <OUTPUT-EXTENSION> Selects the output file extension or container.
        <OUTPUT-BITRATE>   Selects the output file bitrate, in kbps

    for example, the flag with the following rule:

        --ffmpeg flac:libopus:ogg:192k

    instructs the script to convert all FLAC files into opus, using .ogg containers,
    with bitrate of 192 kbps. The metadata is copied as-is.
    """  # noqa: E122

    p = argparse.ArgumentParser(description=description,
                                epilog=textwrap.dedent(_epilog),
                                formatter_class=argparse.RawDescriptionHelpFormatter)

    # I don't like positional arguments. They are too implicit.
    # Let's be explicit and use --arguments instead
    p.add_argument("--indir", required=True,
                   help="Input directory. Files in this directory are not modified.")
    p.add_argument("--outdir", required=True,
                   help="Output directory. Files from INDIR are copied or mapped here")
    p.add_argument("--ignore", action='append',
                   help=("Neither copy nor map files with these extensions. "
                         "Glob-pattern aware. For example: --ignore '*.jpg'"))
    p.add_argument("--ffmpeg", nargs='+', action=FFMPEGRuleAction, metavar='FFMPEG_RULE',
                   help=("Transcode matching audio files with ffmpeg. "
                         "See FFMPEG_RULE description below"))
    p.add_argument("--concurrency", default=cpu_count(), metavar='NJOBS', type=int,
                   help="Number of parallel workers to use. Default value == available cpu count.")
    p.add_argument("--verbose", help="Be more verbose", action='store_true')

    args = p.parse_args(argv[1:])

    return args


def _main(indir, outdir, ffmpeg_map=None, ignore_patts=None, concurrency=1, verbose=False):
    """
    Main function of copy-tree-map

    Arguments:

    indir
        The input directory
    outdir
        The output directory, must not exist already
    ffmpeg_map
        A dictionary of dictionaries; instructions on how to convert input
        audio file (by extension - the toplevel keys) into some other format (the
        value-dictionary). For example, the following ffmpeg_map:
            {'flac': {'codec': 'libopus', 'ext': 'ogg', 'bitrate': '192k'}}
        tells that all input .flac files are to be converted into ogg/opus files with
        bitrate 192 kbps.
    ignore_patts
        List of strings; glob-patterns of input files which to ignore.
    concurrency
        Number of parallel workers to use
    """
    indir = str(indir)
    outdir = str(outdir)
    ffmpeg_map = ffmpeg_map or {}
    ignore_patts = ignore_patts or []
    concurrency = max(1, concurrency)

    ignored = []
    futures = []
    failed = []

    # Construct the ignore_patterns object object for shutil.copytree()
    ign_patts = shutil.ignore_patterns(*ignore_patts)

    # Helper function that captures filenames that are ignored by shutil.copytree
    # Not really needed, except for debugging in verbose mode
    def ignorefn(*fooargs, **fookwargs):
        ret = ign_patts(*fooargs, **fookwargs)
        if ret:
            ign = list(ret)
            if verbose:
                print(">> [IGNR] '{}'".format(', '.join(f for f in ign)))
            ignored.extend(ign)
        return ret

    # Uh... we are running subprocesses inside the threads...?
    # The threads don't do much, just wait for the subprocess to finish :)
    # TODO: use asyncio or something...
    with ThreadPoolExecutor(max_workers=concurrency) as pool:

        # Produce a function with the appropriate copy_function signature
        # that copytree() expects
        mycopy = functools.partial(_mycopy, pool, futures,
                                   ffmpeg_map, verbose=verbose)

        try:
            shutil.copytree(indir, outdir, ignore=ignorefn, copy_function=mycopy)
        except FileExistsError as e:
            print("ERROR - File or directory already exists: '{}'".format(e.filename))
            return -2

        if verbose:
            print("---")

        for fut in as_completed(futures):
            res = fut.result()
            if verbose:
                status = ["FAILURE", "SUCCESS"][res["success"]]
                print("<< [{}] {} -> {}".format(status, res["src"], res["dst"]))
            if res["success"]:
                continue
            failed.append(res)
            warn = "WARNING: the operation '{}' from '{}' to '{}' failed: {}"
            print(warn.format(res["cmd"][0], res["src"], res["dst"], res["msg"]), file=sys.stderr)

        if verbose:
            print("---")

    n_futs = len(futures)
    n_ign  = len(ignored)
    n_fail = len(failed)
    n_tot  = n_futs + n_ign
    n_ok   = n_tot - n_fail  - n_ign

    if n_fail > 0:
        print("WARNING: there were errors. One or more files were not copied/converted.",
              file=sys.stderr)

    print("Finished. Success: {}, Ignored: {}, Failed: {} (Total: {})".format(n_ok, n_ign,
                                                                              n_fail, n_tot))
    return -1 if n_fail else 0


def main():
    args = parse_args(sys.argv)
    sys.exit(_main(args.indir, args.outdir, ignore_patts=args.ignore, ffmpeg_map=args.ffmpeg,
                   concurrency=args.concurrency, verbose=args.verbose))


if __name__ == "__main__":
    main()
