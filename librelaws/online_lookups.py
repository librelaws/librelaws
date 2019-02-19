from datetime import date, datetime
from glob import glob
from os import path
from os.path import dirname, basename, join
from urllib.parse import urlencode, urlparse
import os
import re

import requests
from lxml import etree

from librelaws.xml_operations import transform_bip_html_to_cropped_html


def get_links_gii():
    """
    Download and parse the "TOC" of gesetze-im-internet.de.

    Return
    ------
    list: Links to all laws found on the site as `zip` files
    """
    root = "http://www.gesetze-im-internet.de/"
    toc = "gii-toc.xml"
    tree = etree.parse(root + toc)
    links = [el.text for el in tree.xpath('//link')]
    return links

def lookup_history(url):
    """
    Lookup the history of a given file on the internet archive
    """
    api_root = "http://web.archive.org/cdx/search/cdx?url="
    search = api_root + url
    resp = requests.get(search)
    resp.raise_for_status()
    keys = ["urlkey","timestamp","original","mimetype","statuscode","digest","length"]
    links = []
    retrieve_root = "https://web.archive.org/web/"
    for l in resp.text.splitlines():
        d = {k: v for (k, v) in zip(keys, l.split())}
        # eg. 20121223155642/https://www.gesetze-im-internet.de/bgb/xml.zip
        links.append(join(retrieve_root, d["timestamp"], d["original"]))
    return links

def save_response(resp, date, dl_dir, rename_to=None):
    """
    Save a response into the local `date/abbrevation/*.zip` hierarchy. If
    `rename_to` is specified rename the file appropriately.
    The response must either be from the internet archive or to `gesetze-im-internet.de`
    """
    url = resp.url()
    if rename_to is None:
        rename_to = path.filename(url)
    if url.contains('web.archive.org'):
        match = re.findall(r'\d{14}')[0]
        d = datetime.strptime("%Y%m%d%H%M%S", match)
    elif url.contains('www.gesetze-im-internet.de'):
        d = datetime.now()
    else:
        raise ValueError("Expected archive.org or gesetze-im-internet.de url. Found: {}".format(url))
    abbrev = path.basename(path.dirname(url))
    ts = d.date.isoformat()
    dirname = path.join(dl_dir, ts, abbrev)

    # Make sure the path exists
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    path_to_file = path.join(dirname, rename_to)
    with open(path_to_file, 'w') as f:
        f.write(response.content)
    return path_to_file


def _get_latest_etag_for_link(dl_folder, link):
    """
    Check if a version of this link has already bean downloaded and if
    so, return the ETag of that version
    """
    # The parentfolder of the zip file is the abbreviated title of the
    # law and also used locally
    url = urlparse(link)
    name = basename(dirname(url.path))
    versions = glob(join(dl_folder, '**', name, '*.zip'), recursive=True)
    # sort by date (part of the path) and pick the newest (last)
    if not versions:
        return None
    newest = max(versions)
    # Filename without the `.zip` part == ETag
    etag = basename(newest)[:-4]
    return etag


def download_zipped_file_if_newer(dl_dir, link):
    """
    Download `link` into the file hierarchy at `dl_dir` if its newer
    than a potential local version.

    Return
    ------
    [string | None]: Path to local file if it was downloaded else `None`
    """
    url = urlparse(link)

    etag_local = _get_latest_etag_for_link(dl_dir, link)
    if etag_local is not None:
        headers = {'If-None-Match': '"{}"'.format(etag_local)}
    else:
        headers = None
    r = requests.get(link, headers=headers)
    r.raise_for_status()
    # is unchanged?
    if r.status_code == 304:
        return None
    etag = r.headers['ETag'].strip('"')
    today = date.today().isoformat()
    # remove leading / to make the later join easier
    rel_path = url.path.strip('/')
    # Compute the dirname including the dlfolder but excluding the file
    dname = dirname(path.join(dl_dir, today, rel_path))
    if not os.path.exists(dname):
        os.makedirs(dname)
    file_path = os.path.join(dname, etag + '.zip')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    return file_path


def bgbl_citation_date(part, year, page):
    """
    Lookup the date of a BGBl citation at api.offenegesetze.de. This
    date cannot be easily found in the xml files.

    Parameters
    ----------
    part: int
        Either `1` or `2`
    year, page: int

    Return
    ------
    datetime:
        The date at which this BGBl was published
    """
    params = {
        'year': year,
        'kind': "bgbl{}".format(part),
        'page': page,
    }
    root = "https://api.offenegesetze.de/v1/veroeffentlichung/"
    resp = requests.get(root, params=params)
    resp.raise_for_status()
    j = resp.json()['results']
    try:
        date = j[0]['date']
    except IndexError:
        raise ValueError("No results found for provided parameters")
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


def search_bundestag_dip(publication, bgbl_year, bgbl_page):
    """
    Search `dipbt.bundestag.de` for details concerning the proceedings of the given BGBl entry.
    The results have to be extracted from the returned html. The return HTML may not have any results.

    Return
    ------
    lxml.Element:
        The response parse as an HTML document

    Example
    -------
    search_bundestag_dip('BGBl I', 2019, 54)
    """
    req_url = 'http://dipbt.bundestag.de/dip21.web/searchProcedures/advanced_search_list.do'
    headers = _create_headers_bip()
    query = _create_request_data_bip(publication, bgbl_year, bgbl_page)
    r = requests.post(req_url, data=query, headers=headers, )
    r.raise_for_status()
    html = etree.HTML(r.text)
    return transform_bip_html_to_cropped_html(html)


def _create_headers_bip():
    """
    Somehow, some of the cookies are not properly set by request.
    This function creates a custom header to be used when searching bip21
    """
    r = requests.get('http://dipbt.bundestag.de/dip21.web/bt')
    cookie_pattern = r'[A-Z]*=\w*\.dip21'
    cookies = re.findall(cookie_pattern, r.headers['Set-Cookie'], )
    headers = {
        'Cookie': '; '.join(cookies),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    return headers


def _create_request_data_bip(publication, bgbl_year, bgbl_page):
    """
    Create the request string to query bundestag.de

    Parameters
    ----------
    publication: str
        {'BGBl I', 'BGBl II'}
    bgbl_year, bgbl_page: int

    Return
    ------
    str: Formated and escaped query string ready to be used by Requests
    """
    supported_pubs = [
        'BGBl I', 'BGBl II'
    ]
    if publication not in supported_pubs:
        raise ValueError("{} is not a supported publication".format(publication))
    d = {
        'drsId': '',
        'plprId': '',
        'aeDrsId': '',
        'aePlprId': '',
        'vorgangId': '',
        'procedureContext': '',
        'vpId': '',
        'formChanged': 'false',
        'promptUser': 'false',
        'overrideChanged': 'true',
        'javascriptActive': 'yes',
        'personId': '',
        'personNachname': '',
        'prompt': 'no',
        'anchor': '',
        'wahlperiodeaktualisiert': 'false',
        'wahlperiode': '',
        'startDatum': '',
        'endDatum': '',
        'includeVorgangstyp': 'UND',
        'nummer': '',
        'suchwort': '',
        'suchwortUndSchlagwort': 'ODER',
        'schlagwort1': '',
        'linkSchlagwort2': 'UND',
        'schlagwort2': '',
        'linkSchlagwort3': 'UND',
        'schlagwort3': '',
        'unterbegriffsTiefe': 0,
        'sachgebiet': '',
        'includeKu': 'UND',
        'ressort': '',
        'nachname': '',
        'vorname': '',
        'verkuendungsblatt': publication,
        'jahrgang': bgbl_year,
        'heftnummer': '',
        'seite': bgbl_page,
        'verkuendungStartDatum': '',
        'verkuendungEndDatum': '',
        'btBrBeteiligung': 'alle',
        'gestaOrdnungsnummer': '',
        'beratungsstand': '',
        'signaturParlamentsarchiv': '',
        'method': 'Suchen',
    }
    return d