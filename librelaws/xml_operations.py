from datetime import date
from os import path
import re
import zipfile

from lxml import etree


def zip_to_xml(file):
    """
    Parse the first xml file found in a zip `file` downloaded from
    `gesetze-im-internet.de`.

    Return
    ------
    etree: Parsed xml file
    """
    with zipfile.ZipFile(file) as zf:
        fname = [i.filename for i in zf.infolist() if ".xml" in i.filename][0]
        return etree.parse(zf.open(fname))


def transform_gii_xml_to_html(xml):
    """
    Transfom the xml format of `gesetze-im-internet.de`
    """
    # First transform to html via xslt, then to md using pandoc
    xsl_file = path.join(path.dirname(path.abspath(__file__)), 'assets', 'gii_xml_to_html.xsl')
    xslt_root = etree.parse(xsl_file)
    transform = etree.XSLT(xslt_root)
    # The resulting `html` object is an etree
    return transform(xml)


def transform_bip_html_to_cropped_html(html):
    """
    Crop the messy html returned from a BIP search to the bare essentials
    """
    # First transform to html via xslt, then to md using pandoc
    xsl_file = path.join(path.dirname(path.abspath(__file__)), 'assets', 'crop_bip_html.xsl')
    xslt_root = etree.parse(xsl_file)
    transform = etree.XSLT(xslt_root)
    # The resulting `html` object is an etree
    return transform(html)


class Citation:
    def __init__(self, day, month, year, part, page):
        self.date = date(int(year), int(month), int(day))
        self.part = part
        self.page = int(page)


def get_citation_from_standkommentar_node(xml):
    """
    Try to extract the citation from the 'standcommentar' node of an
    xml file from `gesetze-im-internet.de`. This citation should point
    to the latest change done to this law. If not found, it probably
    means that it is novel.

    Parameter
    ---------
    xml: etree
        Parsed xml file from `gesetze-im-internet.de`

    Return
    ------
    Citation: The identified citation

    Raises
    ------
    ValueError: If no citation could be identified
    """
    comment = xml.find("//standangabe/standkommentar[last()]")
    if comment is None:
        raise ValueError("Xml has no `standkommentar` nodes")
    pattern = r'\w\. (\d{1,2})\.(\d{1,2})\.(\d{4})\s(\w+)\s(\d+)'
    matches = re.findall(pattern, comment.text)
    citations = [Citation(*m) for m in matches]
    if len(citations) == 0:
        raise ValueError("Could not identify citation")
    # Return the newst citation
    return sorted(citations, key=lambda c: c.date)[-1]


def get_origin_gazette(xml):
    """
    Try to find the gazette which first published this law. Note that
    there might have been changes in the meantime! Try using
    `get_citation_from_standkommentar_node` first.

    Return
    ------
    [dict | None]: With keys 'gazette', 'year', and 'page'
    """
    # from online_lookups import bgbl_citation_date
    try:
        # <periodikum>BGBl I</periodikum>
        # <zitstelle>2019, 58</zitstelle>
        per = xml.find("//fundstelle/periodikum").text
        zit = xml.find("//fundstelle/zitstelle").text
    except AttributeError:
        # raise ValueError("No 'fundstelle' specified in xml.")
        return None
    if 'BGBl' not in per:
        return None
    pattern = r'\A(\d{4}), (\d+)'
    matches = re.findall(pattern, zit)
    if len(matches) == 0:
        return None
    (year, page) = matches[0]
    return {"gazette": per, "year": int(year), "page": int(page)}
