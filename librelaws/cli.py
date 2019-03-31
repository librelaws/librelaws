import argparse
import concurrent.futures
import logging
from os.path import dirname, basename

from requests import get
from tqdm import tqdm

from librelaws import online_lookups, fs_operations, xml_operations
from librelaws.online_lookups import (
    download_gii_if_non_existing, lookup_history, search_bundestag_dip
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
    return parser


def add_git_subparser(subparsers):
    description = 'Build a git history based on the content of `download-dir`.'
    parser_git = subparsers.add_parser('git', description=description)
    parser_git.add_argument(
        'git-dir',
        help='Directory where the git repository will be created. Must not be `download-dir`.'
    )


def add_dl_subparser(subparsers):
    parser_dl = subparsers.add_parser('download', description='Download items into the `download-dir`')
    parser_dl.add_argument(
        '-F', '--force', action='store_true', default=False,
        help='Download items even if they already exist locally')
    parser_dl.add_argument(
        '--source', choices=['gii', 'archive.org'], required=True,
        help=('The source from which to download. `gesetze-im-internet.de` only serves the latest '
              'versions of each law, while `archive.org` may be incomplete. '))
    parser_dl.set_defaults(func=do_download)


def do_download(args):
    source = args.source
    dl_dir = args.__getattribute__('download-dir')
    links = online_lookups.get_links_gii()

    if source == 'gii':
        updates = []
        etags = online_lookups.get_dict_folder_etag(dl_dir)
        def parent_folder_name(url):
            return basename(dirname(url))

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            # We cannot rely on any etags in this case so we just download it all
            futures = [
                executor.submit(download_gii_if_non_existing, dl_dir, url, etag=parent_folder_name(url)) for url in links
            ]
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc='Downloading...'):
                path = future.result()
                if path is not None:
                    updates.append(path)
        print("{} new files were downloaded".format(len(updates)))

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

