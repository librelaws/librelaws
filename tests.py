from datetime import datetime
import os
from os import path
from unittest import TestCase, skip
import tempfile
from datetime import date

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
            path = online_lookups.download_gii_if_non_existing(tmpdirname, link)
            self.assertTrue(path is not None)
            # Now the file was not downloaded again
            etags = online_lookups.get_dict_folder_etag(tmpdirname)

            law_abbrev = os.path.basename(os.path.dirname(link))
            etag = etags[law_abbrev]
            path = online_lookups.download_gii_if_non_existing(tmpdirname, link, etag=etag)
            self.assertTrue(path is None)


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
        html = etree.HTML(html)
        self.assertGreater(len(html), 0)
        # Crop html
        xml_operations.transform_bip_html_to_cropped_html(html)


class TestEtag(TestCase):
    def test_create_etag_table(self):
        online_lookups.get_dict_folder_etag("~/repos/giidl/mytestdir/")


class TestXmlOperations(TestCase):
    def test_open_zip_convert_to_html(self):
        link = online_lookups.get_links_gii().pop()
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Should always download the file since there is no local
            # version in the folder
            fname = online_lookups.download_gii_if_non_existing(tmpdirname, link)
            xml = xml_operations.zip_to_xml(fname)
            self.assertGreater(len(xml.getroot()), 0)
            # Convert to html
            html = xml_operations.transform_gii_xml_to_html(xml)
            self.assertGreater(len(html.getroot()), 0)

    def test_find_citation(self):
        xml_file = path.join(path.dirname(path.abspath(__file__)), 'test_files', 'StGB_pretty.xml')
        xml = etree.parse(xml_file)
        xml_operations.Citation.from_standkommentar_node(xml)

    # @skip
    def test_find_all_local_files(self):
        """Require to have some local files stored"""
        import logging
        files = fs_operations.all_local_files("~/archive_laws")
        for f in files:
            xml = xml_operations.zip_to_xml(f)
            try:
                xml_operations.Citation.from_standkommentar_node(xml)
            except Exception as e:
                try:
                    cit = xml_operations.Citation.from_fundstelle_node(xml)
                    logging.debug("Converted on second try: {} {} {}".format(cit.gazette, cit.year, cit.page))
                except ValueError as e:
                    pass  # logging.warning(e)

    # @skip
    def test_origin_citation(self):
        """Require to have some local files stored"""
        import logging
        files = fs_operations.all_local_files("~/repos/giidl/mytestdir/")
        for f in files:
            xml = xml_operations.zip_to_xml(f)
            try:
                xml_operations.Citation.from_fundstelle_node(xml)
            except ValueError as e:
                logging.warning(e)


class TestCli(TestCase):
    def test_wrong_source(self):
        with self.assertRaises(Exception):
            args = parser.parse_args(['tmpdirname', 'download', '--source', 'not-a-source'])

    @skip
    def test_dl_gii(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            parser = cli.create_parser()
            args = parser.parse_args(['tmpdirname', 'download', '--source', 'gii'])
            args.func(args)
            # Should not crash if we try to download the same things again; just skipping
            args.func(args)

    @skip
    def test_dl_archive(self):
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
        hash1 = fs_operations.hash_without_builddate(xml1)
        hash2 = fs_operations.hash_without_builddate(xml2)
        hash3 = fs_operations.hash_without_builddate(xml3)
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)

class TestGit(TestCase):
    def test_author(self):
        git.cabinet_sig(date(day=17, month=12, year=2013))
        git.cabinet_sig(datetime(day=17, month=12, year=2013))


def test_do_git():
    import concurrent.futures

    files = fs_operations.all_local_files('~/archive_laws')
    files_with_cit = []
    for f in files[:100]:
        xml = xml_operations.zip_to_xml(f)
        try:
            cit = xml_operations.Citation.from_xml(xml)
        except ValueError:
            continue
        if cit.gazette in ['BGBl I', 'BGBl II']:
            files_with_cit.append((f, cit))
    print("Number of queries: ", len(files_with_cit))
    # Since want to build a git history its important that we get the order right.
    # We do all th searches upfornt and than sort again
    with concurrent.futures.ProcessPoolExecutor(max_workers=30) as executor:
        future_to_file = {
            executor.submit(online_lookups.search_bundestag_dip, cit.gazette, cit.year, cit.page): f
            for (f, cit) in files_with_cit
        }
    for future in concurrent.futures.as_completed(future_to_file):
        f = future_to_file[future]
        future.result()
