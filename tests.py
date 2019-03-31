from datetime import datetime
from os import path
from unittest import TestCase, skip
import tempfile
from datetime import date, datetime

from lxml import etree

from librelaws import (
    online_lookups, xml_operations, fs_operations, cli, git
)


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
            res = online_lookups.download_gii_if_non_existing(tmpdirname, link)
            online_lookups.save_response(res, tmpdirname)
            self.assertTrue(res is not None)
            # Now the file was not downloaded again
            with self.assertRaises(online_lookups.VersionExistsError):
                online_lookups.download_gii_if_non_existing(tmpdirname, link)


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

class TestEtag(TestCase):
    def test_create_etag_table(self):
        online_lookups.get_dict_folder_etag("~/repos/giidl/mytestdir/")


class TestXmlOperations(TestCase):
    def test_open_zip_convert_to_html(self):
        link = online_lookups.get_links_gii().pop()
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Should always download the file since there is no local
            # version in the folder
            res = online_lookups.download_gii_if_non_existing(tmpdirname, link)
            fname = online_lookups.save_response(res, tmpdirname)
            xml = xml_operations.zip_to_xml(fname)
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

class TestCli(TestCase):
    def test_wrong_source(self):
        with self.assertRaises(Exception):
            args = parser.parse_args(['tmpdirname', 'download', '--source', 'not-a-source'])

    def test_dl_gii(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            parser = cli.create_parser()
            args = parser.parse_args(['tmpdirname', 'download', '--source', 'gii'])
            args.func(args)
            # Should not crash if we try to download the same things again; just skipping
            args.func(args)

    def test_dl_gii(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            parser = cli.create_parser()
            args = parser.parse_args(['tmpdirname', 'download', '--source', 'archive.org'])
            args.func(args)
            # Should not crash if we try to download the same things again; just skipping
            args.func(args)


class TestBuilddate(TestCase):
    def test_build_date_differences(self):
        xml1 = etree.XML('<a><b builddate="20130405132018">Text</b></a>')
        xml2 = etree.XML('<a><b>Text</b></a>')
        xml3 = etree.XML('<a><c>Text</c></a>')
        hash1 = fs_operations._hash_without_builddate(xml1)
        hash2 = fs_operations._hash_without_builddate(xml2)
        hash3 = fs_operations._hash_without_builddate(xml3)
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)

    @skip
    def test_hash_all_files(self):
        """
        This is really not a test but rather a way to clean up duplicates. Should be in the Cli
        """
        import os
        files = fs_operations.all_local_files("~/archive_laws")
        seen = {}
        for f in files:
            try:
                xml = xml_operations.zip_to_xml(f)
            except:
                print("Broken zip file: ", f)
                continue
            h = fs_operations._hash_without_builddate(xml)
            same = seen.get(h, [])
            same.append(f)
            seen[h] = same
        dups_list = [sorted(fs) for fs in seen.values() if len(fs) > 1]
        # Go through all seen duplicates (note: list of lists!)
        for dups in dups_list:
            # Remove duplicate files and empty folders; keep newst version
            for dup in dups[:-1]:
                os.remove(dup)
                try:
                    # abbrev folder; may not be empty if we combined archive.org and gii
                    os.rmdir(path.dirname(dup))
                    # Date folder
                    os.rmdir(path.dirname(path.dirname(dup)))
                except OSError:
                    pass
