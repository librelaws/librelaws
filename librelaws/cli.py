import argparse
import concurrent.futures
import logging
import os
from os.path import dirname, basename

import requests
from requests import get
from tqdm import tqdm
import pygit2

from librelaws import online_lookups, fs_operations, git
from librelaws.online_lookups import (
    download_gii_if_non_existing, lookup_history
)


def create_parser():
    """
    Creates the parser object

    By using a function, the parser is also easily available for unittests
    """
    class formatter_class(argparse.ArgumentDefaultsHelpFormatter,
                          argparse.RawTextHelpFormatter):
        pass
    parser = argparse.ArgumentParser(formatter_class=formatter_class)
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False)
    parser.add_argument('download-dir', help='Destination directory for the downloaded files')
    subparsers = parser.add_subparsers()
    # Download related actions
    add_dl_subparser(subparsers)
    add_git_subparser(subparsers)
    add_clean_subparser(subparsers)
    return parser


def add_git_subparser(subparsers):
    description = 'Build a git history based on the content of `download-dir`.'
    parser_git = subparsers.add_parser('git', description=description)
    parser_git.add_argument(
        'git-dir',
        help='Directory of the git repository. Must not be `download-dir`.'
    )
    parser_git.set_defaults(func=do_git)


def add_dl_subparser(subparsers):
    parser_dl = subparsers.add_parser('download', description='Download items into the `download-dir`')
    parser_dl.add_argument(
        '-F', '--force', action='store_true', default=False,
        help='Download items even if they already exist locally')
    parser_dl.add_argument(
        '--source', choices=['gii', 'archive.org'], required=True,
        help=('The source from which to download. `gesetze-im-internet.de` only serves the latest '
              'versions of each law, while `archive.org` may be incomplete. '))
    parser_dl.add_argument(
        '--quiet', default=False, help='Disable progress bar', action='store_true'
    )
    parser_dl.set_defaults(func=do_download)


def add_clean_subparser(subparsers):
    parser = subparsers.add_parser('clean', description='Delete duplicates from the `download-folder` keeping the oldest versions')
    parser.set_defaults(func=do_clean)


def do_download(args):
    source = args.source
    dl_dir = args.__getattribute__('download-dir')
    quiet = args.quiet
    links = online_lookups.get_links_gii()

    if source == 'gii':
        updates = []
        etags = online_lookups.get_dict_folder_etag(dl_dir)

        def etag_for_url(url):
            k = basename(dirname(url))
            return etags.get(k, None)
        request_excs = []
        other_excs = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            # We cannot rely on any etags in this case so we just download it all
            futures = [
                executor.submit(download_gii_if_non_existing, dl_dir, url, etag=etag_for_url(url)) for url in links
            ]
            for future in tqdm(futures, disable=quiet):  # concurrent.futures.as_completed(futures, timeout=2):
                try:
                    path = future.result()
                except requests.exceptions.RequestException as e:
                    request_excs.append(e.request.url)
                except Exception as exc:
                    other_excs.append(exc)
                if path is not None:
                    updates.append(path)
        print("{} new files were downloaded".format(len(updates)))
        print("Timed out urls: \n {}".format(request_excs))
        print("Exceptions: ", other_excs)

    # TODO: This part is out of date!
    if source == 'archive.org':
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            hist_links = executor.map(lookup_history, links)
            hist_links = tqdm(hist_links, desc='Collecting links...', total=len(links))
            flat_links = [item for sublist in hist_links for item in sublist]
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            # We cannot rely on any etags in this case so we just download it all
            futures = [
                executor.submit(get, url) for url in flat_links
            ]
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc='Downloading...'):
                try:
                    resp = future.result()
                except online_lookups.VersionExistsError as exc:
                    logging.info('%r exists locally. Skipping it.' % (exc))
                    continue
                online_lookups.save_response(resp, dl_dir)


def do_clean(args):
    dl_dir = args.__getattribute__('download-dir')
    files = sorted(fs_operations.all_local_files(dl_dir))
    dups = fs_operations.find_duplicates(files)
    for dup in dups:
        os.remove(dup)
        try:
            # abbrev folder; may not be empty if we combined archive.org and gii
            os.rmdir(dirname(dup))
            # Date folder
            os.rmdir(dirname(dirname(dup)))
        except OSError:
            # Folder was not empty
            pass
    print("Removed {} duplicates leaving {} unique files.".format(len(dups), len(files) - len(dups)))


def do_git(args):
    dl_dir = args.__getattribute__('download-dir')
    git_dir = args.__getattribute__('git-dir')
    print(dl_dir, git_dir)
    repo_path = pygit2.discover_repository(git_dir)
    if repo_path is None:
        repo = pygit2.init_repository(git_dir)
    else:
        repo = pygit2.Repository(repo_path)
    files = fs_operations.all_local_files(dl_dir)
    augmented_files = git.augment_and_filter_files(files)
    for (f, cit, aug) in augmented_files:
        msg = git.prepare_commit_message(f, aug)
        git.commit_update(f, cit, msg, repo)
