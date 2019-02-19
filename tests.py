from datetime import datetime
from os import path
from unittest import TestCase, skip
import tempfile

from lxml import etree

from librelaws import online_lookups, xml_operations, fs_operations


class TestGesetzeImInternet(TestCase):
    """
    Various tests centered around interactions with gesetze-im-internet.de
    """
    def test_get_links(self):
        links = online_lookups.get_links_gii()
        self.assertGreater(len(links), 0)

    def test_get_zipped_law_if_newer(self):
        link = online_lookups.get_links_gii().pop()
        with tempfile.TemporaryDirectory() as tmpdirname:
            res = online_lookups.download_zipped_file_if_newer(tmpdirname, link)
            self.assertTrue(res is not None)
            # Now the file was not downloaded again
            res = online_lookups.download_zipped_file_if_newer(tmpdirname, link)
            self.assertTrue(res is None)

class TestInternetArchive(TestCase):
    def test_lookup_bgb(self):
        url = "https://www.gesetze-im-internet.de/bgb/xml.zip"
        links = online_lookups.lookup_history(url)
        print(links)
        self.assertGreater(len(links), 11)


class TestOffenegesetzeApi(TestCase):
    def test_date_lookup(self):
        found = online_lookups.bgbl_citation_date(1, 2019, 58)
        should = datetime(2019, 2, 5, 0, 0)
        self.assertEqual(found, should)


class TestBipApi(TestCase):
    def test_procedure_lookup(self):
        html = online_lookups.search_bundestag_dip('BGBl I', 2019, 54)
        self.assertGreater(len(html.getroot()), 0)


class TestXmlOperations(TestCase):
    def test_open_zip_convert_to_html(self):
        link = online_lookups.get_links_gii().pop()
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Should always download the file since there is no local
            # version in the folder
            res = online_lookups.download_zipped_file_if_newer(tmpdirname, link)
            xml = xml_operations.zip_to_xml(res)
            self.assertGreater(len(xml.getroot()), 0)
            # Convert to html
            html = xml_operations.transform_gii_xml_to_html(xml)
            self.assertGreater(len(html.getroot()), 0)

    def test_find_citation(self):
        xml_file = path.join(path.dirname(path.abspath(__file__)), 'test_files', 'StGB_pretty.xml')
        xml = etree.parse(xml_file)
        xml_operations.get_citation_from_standkommentar_node(xml)

    @skip
    def test_find_all_local_files(self):
        """Require to have some local files stored"""
        files = fs_operations.all_local_files("~/repos/giidl/mytestdir/")
        for f in files:
            xml = xml_operations.zip_to_xml(f)
            print(f)
            xml_operations.get_citation_from_standkommentar_node(xml)

    @skip
    def test_origin_citation(self):
        """Require to have some local files stored"""
        files = fs_operations.all_local_files("~/repos/giidl/mytestdir/")
        for f in files:
            xml = xml_operations.zip_to_xml(f)
            print(f)
            xml_operations.get_origin_gazette(xml)
