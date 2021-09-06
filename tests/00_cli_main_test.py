from copy_tree_map import _main
import pathlib
import sys

here = pathlib.Path(__file__).parent.resolve()

# hacky hack. We want to test what happens when a file is non-readable.
# Ideally this file should be in git, but it is difficult to add with
# the correct permissons (chmod a-rwx)
cantread = pathlib.Path(here / 'example' / 'foo' / 'cantread')
cantread.touch(mode=0, exist_ok=True)

# TODO: refactor the code for easier testing

def test_main_without_error_noignore(tmp_path):
    indir = (here / 'example')
    tmp_path.rmdir()
    ignore = ["*cantread*"] # besides this, of course...
    ret = _main(indir, tmp_path, ignore_patts=ignore, concurrency=1)
    assert ret == 0

    expected_files = [
        "beep.flac",
        "bar",
        "should-not-be-here.md",
        "bar/hello2-noignore.txt",
        "foo",
        "foo/beep.m4a",
        "hello1-noignore.txt"
    ]
    assert tmp_path.exists()

    for expected in expected_files:
        assert (tmp_path / expected).exists()


def test_main_without_error_with_ignore(tmp_path):
    indir = (here / 'example')
    ignore = ["*.md", "*notouchme*", "*cantread*"]
    tmp_path.rmdir()
    ret = _main(indir, tmp_path, ignore_patts=ignore, concurrency=1)
    assert ret == 0

    expected_files = [
        "beep.flac",
        "bar",
        "bar/hello2-noignore.txt",
        "foo",
        "foo/beep.m4a",
        "hello1-noignore.txt"
    ]
    assert tmp_path.exists()

    for expected in expected_files:
        assert (tmp_path / expected).exists()


def test_main_ffmpeg_conv_noerror(tmp_path):
    indir = (here / 'example')
    ignore = ["*.md", "*notouchme*", "*cantread*"]
    ffmpeg_map = {"m4a": {"codec": "libopus", "ext": "ogg", "bitrate": "54k"}}
    tmp_path.rmdir()
    ret = _main(indir, tmp_path, ignore_patts=ignore, ffmpeg_map=ffmpeg_map, concurrency=1)
    assert ret == 0

    expected_files = [
        "beep.flac",
        "bar",
        "bar/hello2-noignore.txt",
        "foo",
        "foo/beep.ogg",
        "hello1-noignore.txt"
    ]
    assert tmp_path.exists()

    for expected in expected_files:
        assert (tmp_path / expected).exists()

def test_main_witherror(tmp_path):
    indir = (here / 'example')
    ignore = ["*.md", "*notouchme*"] # cannot read file marked "*cantread*"
    tmp_path.rmdir()
    ret = _main(indir, tmp_path, ignore_patts=ignore, concurrency=1)
    assert ret == -1 # success, but there were errors


