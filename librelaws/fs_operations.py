from os import path
from glob import glob

from lxml import etree

from .xml_operations import zip_to_xml


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


def local_versions(dl_dir, uri):
    """
    Find the local zip-files related to the given a Uri (Url or local path)

    Parameters
    ----------
    dl_dir: string
        Download directory where the local files are stored
    uri: string
        A Url or path to a zipped xml file
    """
    # We expect the path to end with `date/[abbrevation]/*.zip`
    abbrev = path.basename(path.dirname(uri))
    search = path.join(path.expanduser(dl_dir), "**", abbrev, "*.zip")
    all_files = glob(search, recursive=True)
    # Oldest files first
    return sorted(all_files)


def version_exists_locally(dl_dir, response):
    """
    Check if a copy of the file produced by this response already
    exists locally. Note that this function produces a lot of
    false-negatives! There are many cases where the only thing changed
    is the `builddate` attribute in some xml tags.
    """
    m = hashlib.sha256()
    m.update(response.content)
    new_hash = m.digest()

    url = response.url
    stored_files = local_versions(dl_dir, url)
    for fname in stored_files:
        with open(fname, 'rb') as f:
            m = hashlib.sha256()
            m.update(f.read())
            if m.digest() == new_hash:
                return True
    return False


def hash_without_builddate(xml):
    """
    Compute a hash for the given xml excluding the builddate attribute
    """
    xsl = etree.XML(b"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <!-- IdentityTransform -->
  <xsl:template match="@* | node()">
      <xsl:copy>
      	<xsl:apply-templates select="@* | node()" />
      </xsl:copy>
  </xsl:template>

  <!-- Drop builddate nodes -->
  <xsl:template match="@builddate">
  </xsl:template>
</xsl:stylesheet>
""")
    transform = etree.XSLT(xsl)
    return hash(etree.tostring(transform(xml)))

def find_duplicates(files):
    """
    Find duplicates in the provided files. The returned files
    **exclude** the first unique copy of each version. Ie. the
    returned list can be deleted.  You probably want to sort the list
    in some way before passing it here.
    """
    d = {}
    for f in files:
        h = hash_without_builddate(zip_to_xml(f))
        if d.get(h, None) is None:
            d[h] = [f]
        else:
            d[h].append(f)
    dups = sum([v[1:] for v in d.values() if len(v) > 1], [])
    return dups
