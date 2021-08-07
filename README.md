# copy-tree-map.py

Copy directory tree with transformations.

Clones a directory tree while possibly filtering and/or transforming files. At
the moment it is mostly useful for copy-transcoding nested directory structures 
containing audio files.

# Usage

Please run:

    $ python3 copy_tree_map.py --help

# Example

We have a directory tree 'foo' with various files, including some lossless
audio files (FLAC):

    foo/
        album.jpg
        readme.txt
        cd1/
            another.txt
            01.flac
            02.flac
            ...
        cd2/
            03.flac
            04.flac
            ...

After running

    $ copy_tree_map.py    \
        --indir foo       \
        --outdir foo_mp3  \
        --ignore "*.txt"  \
        --ffmpeg flac:libmp3lame:mp3:128k

...a new directory `foo_mp3` should have been created with the following contents:

    foo_mp3/
        album.jpg
        cd1/
            01.mp3
            02.mp3
            ...
        cd2/
            03.mp3
            04.mp3
            ...

Note that `readme.txt` and `another.txt` were dropped, and `flac`'s were converted 
to `mp3` files. If you inspect the `mp3` files with `ffmpeg`, you'll notice their
bitrate is 128 kbps.

# Transcoding support

At the moment, the supported output audio formats are
- `libopus`
- `libmp3lame`

The output container type can (or must?) be specified in the `--ffmpeg` option string.
The option format follows `:`-delimited pattern 

    <INPUT-EXTENSION>:<OUTPUT-CODEC>:<OUTPUT-EXT>:<BITRATE>

where
- `INPUT-EXTENSION`: is used for matchin the files in the source directory, e.g `flac`
- `OUTPUT-CODEC`: for example, use `libopus` if you wish to encode to Opus files
- `OUTPUT-EXT`: which file container to use for the resulting file (`ogg`, for example).
- `BITRATE`: encoded audio bitrate, for example `192k`

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

