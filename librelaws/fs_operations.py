from os import path
from glob import glob


def all_local_files(dl_dir):
    """
    Returns a list of paths to all the locally cached files. The list
    is sorted such that the oldest files (by download time) is the
    first item.

    Parameters
    ----------
    dl_dir: string
        Download directory where the local files are stored
    """
    search = path.join(path.expanduser(dl_dir), "**/*.zip")
    all_files = glob(search, recursive=True)
    # Oldest files first
    return sorted(all_files)
