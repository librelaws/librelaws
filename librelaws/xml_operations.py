from datetime import date
from os import path
import re
import zipfile
import logging

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
    def __init__(self, gazette, year, month=None, day=None, page=None, index=None):
        self.year = int(year)
        self.month = int(month) if month is not None else None
        self.day = int(day) if day is not None else None
        if gazette not in ['BGBl I', 'BGBl II', 'VkBl', 'BAnz', 'RGBl']:
            logging.info("Unexpected gazette: {}".format(gazette))
        self.gazette = gazette
        self.page = int(page) if page is not None else None
        self.index = index

    def year(self):
        """Return the year of this citation. This is enough for some lookups
        """
        return self.year

    def date(self):
        """Return full date of this `Citation`. May fail if
        constructed from the `fundstelle` node. In that case we need
        to augment the data from `offenegesetze.de`
        """
        return date(self.year, int(self.month), int(self.day))

    @classmethod
    def from_xml(cls, xml):
        """Try to figure out the latest citation related to this xml
        object. This tries first `from_standkommentar_node` and then
        `from_fundstelle_node`. This is the default way of
        instantiating a `Citation`
        """
        try:
            return cls.from_standkommentar_node(xml)
        except ValueError:
            pass
        return cls.from_fundstelle_node(xml)

    @classmethod
    def from_standkommentar_node(cls, xml):
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
        citations = []
        for m in matches:
            (day, month, year, part, page) = m
            if part == 'I':
                gazette = 'BGBl I'
            elif part == 'II':
                gazette = 'BGBl I'
            else:
                gazette = part
            citations.append(cls(gazette, year, month, day, page))
        if len(citations) == 0:
            raise ValueError("Could not identify citation")
        # Return the newst citation
        return sorted(citations, key=lambda c: c.date())[-1]

    @classmethod
    def from_fundstelle_node(cls, xml):
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
            raise ValueError("Xml has no `fundstelle` nodes")

        # Special casing for Bundesanzeiger Amtlicher Teil (BAnz AT)
        if per == 'BAnz':
            m = re.search(r'\AAT (\d{2})\.(\d{2})\.(\d{4}) (\w+)', zit)
            if m is not None and m.group():
                per += ' ' + 'AT'
                [day, month, year, index] = m.groups()
                return cls(per, year, month, day, index=index)

        pattern = r'\A(\d{4}), (\d+)'
        matches = re.findall(pattern, zit)
        if len(matches) == 0:
            raise ValueError("Unexpected pattern in `zitstelle` node: {}".format(per + ' ' + zit))
        (year, page) = matches[0]
        return cls(per, page=page, year=year)
