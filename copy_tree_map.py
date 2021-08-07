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

import argparse
import functools
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count

#
# Copy directory tree with transformations.
#
# For more information: https://github.com/MawKKe/copy-tree-map
#

# TODO augment when necessary
# Even though .opus extension exists, it is not very well supported (yet). I use .ogg instead.
codec_extmap = { "libopus": ".ogg", "libmp3lame": ".mp3" }

# swap_extensions("foo/bar.flac", "mp3") -> "foo/bar.mp3"
def swap_extension(path, newext):
    newext = [".", ""][newext.startswith(".")] + newext
    a, ext = os.path.splitext(path)
    return a + newext


def ffmpeg_conv(src, dst, codec, bitrate):

    cmd = ["ffmpeg" , "-loglevel", "warning", "-i", src, "-c:a", codec, "-b:a", bitrate, "-vn", dst]

    print(">>>> Launching {0}".format(' '.join(cmd)))

    def inner():
        try:
            proc = subprocess.run(cmd)
            proc.check_returncode()
            return True
        except CalledProcessError as e:
            print(">>>> Error calling ffmpeg: {0}".format(e))
            return False

    ret = inner()

    print(">>>> Conversion '{0}' -> '{1}' done, status: {2}".format(src, dst, ["FAIL", "OK"][ret]))

    return ret


# pool, mapfuncs are arguments passed via partial application.
# the rest follow the signature of shutil.copy & .copy2
def _mycopy(pool, mapfuncs, src, dst, *args, follow_symlinks=True):

    a, ext = os.path.splitext(dst)

    out_params = mapfuncs.get(ext.lstrip("."), None)

    if out_params is not None:
        print(">> Submitting '{0}' into pool to be converted".format(src))

        out_codec   = out_params["codec"]
        out_ext     = out_params["ext"]
        out_bitrate = out_params["bitrate"]

        # Will crash if no such codec exists. This is intended behaviour
        newdest = swap_extension(dst, out_ext)

        pool.submit(ffmpeg_conv, src, newdest, out_codec, out_bitrate)
        return newdest

    else:
        print(">> Copying '{0}' directly (with shutil.copy2)".format(src))
        return shutil.copy2(src,dst,*args,follow_symlinks=follow_symlinks)


# e.g 'flac:libmp3lame:ogg:128k' -> ('flac', 'libmp3lam3', '128k')
PATT = re.compile("([a-zA-Z0-9]+):([a-zA-Z0-9]+):([a-zA-Z0-9]+):(\d+k)")

# Custom 'type' for ArgumentParser. Automatic regex matching during argument parsing! <3
def argument_regex(option, regex=PATT):
    if not regex.match(option):
        raise argparse.ArgumentTypeError(
                "Invalid ffmpeg transformation expression! " + 
                "The format is <INPUT-EXTENSION>:<OUTPUT-CODEC>:<OUTPUT-EXT>:<BITRATE>")
    l = list(filter(None, regex.split(option))) # some silly empty strings in regex.split() output
    if l[1] not in codec_extmap.keys():
        raise argparse.ArgumentTypeError("Unknown codec: {0}".format(l[1]))
    return l[0], {"codec": l[1], "ext": l[2], "bitrate": l[3]}


def main(argv):
    p = argparse.ArgumentParser(description="Copy directory structure and files, " + 
            "possibly filtering and/or mapping (converting) from one format to another")

    # I don't like positional arguments. They are too implicit. 
    # Let's be explicit and use --arguments instead
    p.add_argument("--indir",  required=True, 
            help="Input directory. Files in this directory are not modified.")
    p.add_argument("--outdir", required=True, 
            help="Output directory. Files from INDIR are copied or mapped here")
    p.add_argument("--ignore", action='append', 
            help="Neither copy nor map files with these extensions. Glob-pattern aware. For example: --ignore '*.jpg'")
    p.add_argument("--ffmpeg", action="append", type=argument_regex, 
            help="Convert (audio) with ffmpeg. MAP equals\
            <INPUT-EXTENSION>:<OUTPUT-CODEC>:<BITRATE>. For example: --ffmpeg 'flac:libopus:128k'.\
            Output extension is selected automatically.")
    p.add_argument("--concurrency", default=cpu_count(), 
            help="max_workers value (defaults to your cpu count)", type=int)

    #args = p.parse_args(argv[1:])
    args = p.parse_args()

    #print(args)
    #return 0

    ffmpeg_map = dict(args.ffmpeg)
    print(ffmpeg_map)
    #return 0

    # glob patterns, e.g *.py, *.jpg, foo*
    # NOTE: It is the responsibility of the caller to give proper glob patterns
    ig_patts = list(set(args.ignore)) if args.ignore else None

    #print("ignore:", ig_patts)
    #print("ffmpeg_map:", ffmpeg_map)

    basen = os.path.basename(args.indir)

    outd = args.outdir.replace('{indir_base}', basen)

    ignore = shutil.ignore_patterns(*ig_patts) if ig_patts else None

    print("STARTING")
    print("-"*30)

    # Uh... we are running subprocesses inside the threads...?
    # The threads don't do much, just wait for the subprocess to finish :)
    # TODO: use asyncio or something...
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        mycopy = functools.partial(_mycopy, pool, ffmpeg_map)
        shutil.copytree(args.indir, outd, ignore=ignore, copy_function=mycopy)

    print("-"*30)
    print("DONE")

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
