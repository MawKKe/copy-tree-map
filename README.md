# copy-tree-map

Clones a directory tree while possibly filtering and/or transforming files.

Each file in the input directory tree is processed by exactly one of the transformations:
- copy the file as-is
- transcode the file
- drop the file (i.e do not copy nor transcode it)

Each resulting file is placed in the output directory, in the same relative position
as the original was in the input directory.

At the moment it is mostly useful for transcoding audio files in nested directory
structures. See *Example* below.

# Install

    $ pip install --user git+https://github.com/MawKKe/copy-tree-map

This should place the main script into your user's PATH (`$HOME/.local/bin/` or
similar). Next, see `Usage` below.

# Development and Testing

Clone the repo, and install the package in development mode:

    $ git clone <url> audiobook-split-ffmpeg && cd audiobook-split-ffmpeg
    $ pip install -e '.[dev]'

then run tests with:

    $ pytest -vv

# Usage

Run the following to show all available options:

    $ copy-tree-map --help

Options:
- `--indir <path>`  path of input directory, not modified during the operation
- `--outdir <path>` path of output directory, always created during the operation
- `--ffmpeg <rule>` transcode audio files with ffmpeg, see *Transcoding support* below
- `--ignore <glob>` skip these files altogether; expects a glob pattern (e.g `'*.txt'`") to match files.
- `--concurrency` how many parallel workers are used for `ffmpeg` transcoding operations

**NOTE**: The output directory can exist inside the input directory. The input
directory is scanned fully before any of the output directories or files are created.

**NOTE**: Use single quotes around any glob patterns; otherwise your shell
might expand them before calling the script, causing the rule not to work as expected.

# Example

We have a directory tree `foo/` with various files, including some lossless
audio files (FLAC):

    foo/
        readme.txt
        some/
            deep/
                empty/
                hierarchy/
                    picture.jpg
                    another.png
        bar/
            another.txt
            01.flac
            02.flac
            ...
        baz/
            03.flac
            04.flac
            ...

After running

    $ copy-tree-map \
        --indir foo       \
        --outdir foo_mp3  \
        --ignore '*.txt'  \
        --ffmpeg flac:libmp3lame:mp3:128k

...a new directory `foo_mp3` should have been created with the following structure and contents:

    foo_mp3/
        some/
            deep/
                empty/
                hierarchy/
                    picture.jpg
                    another.png
        bar/
            01.mp3
            02.mp3
            ...
        baz/
            03.mp3
            04.mp3
            ...

Note that
- `readme.txt` and `another.txt` were dropped
- the image files were copied as-is
- the `empty/` directory was created even though there were no files in it.
- the `.flac` files were converted to `.mp3`, with same names but with extensions replaced.

If you inspect the `.mp3` files with `ffmpeg`, you'll notice they are encoded with
`libmp3lame` and have bitrate of 128 kbps.

# Transcoding support

The `--ffmpeg` option can be used for specifying how some (audio) files should  be
transcoded to another formats.

The `--ffmpeg <rule>` has the following `:`-delimited format:

    --ffmpeg <INPUT-EXTENSION>:<OUTPUT-CODEC>:<OUTPUT-EXT>:<BITRATE>

where
- `INPUT-EXTENSION`: is used for matching the files in the source directory, e.g `flac`
- `OUTPUT-CODEC`: for example, use `libopus` if you wish to encode to Opus files
- `OUTPUT-EXT`: which file container to use for the resulting file (`ogg`, for example).
- `BITRATE`: encoded audio bitrate, for example `192k`


**NOTE** - At the moment, the only supported `OUTPUT-CODEC` values are:
- `libopus`
- `libmp3lame`

# Dependencies

- python 3.5 or newer
- ffmpeg if you wish to transcode files

# License

Copyright 2018 Markus Holmström (MawKKe)

The works under this repository are licenced under Apache License 2.0.
See file `LICENCE` for more information.

# Contributing

This project is hosted at https://github.com/MawKKe/copy-tree-map

You are welcome to leave bug reports, fixes and feature requests. Thanks!

