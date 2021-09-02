from copy_tree_map import swap_extension

def test_swapext():    
     assert swap_extension("foo/bar.flac", "mp3") == "foo/bar.mp3"
