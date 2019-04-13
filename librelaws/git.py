from os import path
from datetime import datetime, date

import pygit2
import pypandoc

from .xml_operations import zip_to_xml, transform_gii_xml_to_html, extract_long_name
from .conversion import html_to_markdown


def cabinet_sig(at_date):
    """
    Create a git signature for the cabinet that was in office at the given date

    Parameter
    ---------
    at_date: datetime
        Date used to look up the cabinet
    """
    # make sure we have a datetime
    if isinstance(at_date, type(date.today())):
        at_date = datetime(at_date.year, at_date.month, at_date.day)
    dt = datetime
    cabinets = [
        ('Adenauer cabinet I', dt(day=20, month=9, year=1949), dt(day=20, month=10, year=1953), 'CDU/CSU, FDP, DP'),
        ('Adenauer cabinet II', dt(day=20, month=10, year=1953), dt(day=29, month=10, year=1957), 'CDU/CSU, FDP, GB/BHE, DP'),
        ('Adenauer cabinet III', dt(day=29, month=10, year=1957), dt(day=14, month=11, year=1961), 'CDU/CSU, DP'),
        ('Adenauer cabinet IV', dt(day=14, month=11, year=1961), dt(day=14, month=12, year=1962), 'CDU/CSU, FDP'),
        ('Adenauer cabinet V', dt(day=14, month=12, year=1962), dt(day=17, month=10, year=1963), 'CDU/CSU, FDP'),
        ('Erhard cabinet I', dt(day=17, month=10, year=1963), dt(day=26, month=10, year=1965), 'CDU/CSU, FDP'),
        ('Erhard cabinet II', dt(day=26, month=10, year=1965), dt(day=1, month=12, year=1966), 'CDU/CSU, FDP'),
        ('Kiesinger cabinet', dt(day=1, month=12, year=1966), dt(day=22, month=10, year=1969), 'CDU/CSU, SPD'),
        ('Brandt cabinet I', dt(day=22, month=10, year=1969), dt(day=15, month=12, year=1972), 'SPD, FDP'),
        ('Brandt cabinet II', dt(day=15, month=12, year=1972), dt(day=17, month=5, year=1974), 'SPD, FDP'),
        ('Schmidt cabinet I', dt(day=17, month=5, year=1974), dt(day=16, month=12, year=1976), 'SPD, FDP'),
        ('Schmidt cabinet II', dt(day=16, month=12, year=1976), dt(day=5, month=11, year=1980), 'SPD, FDP'),
        ('Schmidt cabinet III', dt(day=5, month=11, year=1980), dt(day=4, month=10, year=1982), 'SPD, FDP'),
        ('Kohl cabinet I', dt(day=4, month=10, year=1982), dt(day=30, month=3, year=1983), 'CDU/CSU, FDP'),
        ('Kohl cabinet II', dt(day=30, month=3, year=1983), dt(day=12, month=3, year=1987), 'CDU/CSU, FDP'),
        ('Kohl cabinet III', dt(day=12, month=3, year=1987), dt(day=18, month=1, year=1991), 'CDU/CSU, FDP'),
        ('Kohl cabinet IV', dt(day=18, month=1, year=1991), dt(day=17, month=11, year=1994), 'CDU/CSU, FDP'),
        ('Kohl cabinet V', dt(day=17, month=11, year=1994), dt(day=27, month=10, year=1998), 'CDU/CSU, FDP'),
        ('Schröder cabinet I', dt(day=27, month=10, year=1998), dt(day=22, month=10, year=2002), 'SPD, Bündnis 90/Die Grünen'),
        ('Schröder cabinet II', dt(day=22, month=10, year=2002), dt(day=22, month=11, year=2005), 'SPD, Bündnis 90/Die Grünen'),
        ('Merkel cabinet I', dt(day=22, month=11, year=2005), dt(day=28, month=10, year=2009), 'CDU/CSU, SPD'),
        ('Merkel cabinet II', dt(day=28, month=10, year=2009), dt(day=17, month=12, year=2013), 'CDU/CSU, FDP'),
        ('Merkel cabinet III', dt(day=17, month=12, year=2013), dt(day=14, month=3, year=2018), 'CDU/CSU, SPD'),
        ('Merkel cabinet IV', dt(day=14, month=3, year=2018), dt.today(), 'CDU/CSU, SPD'),
    ]
    for c in cabinets:
        if c[1] <= at_date < c[2]:
            email = c[0].split(" ")[0] + '@bundesregierung.de'
            # make sure we have a datetime
            dt = datetime(at_date.year, at_date.month, at_date.day)
            ts = int(dt.timestamp())
            return pygit2.Signature(c[0], email, ts)
    else:
        raise ValueError("No cabinate found for date {}", at_date)


def prepare_commit_message(f, augmented_data):
    """Prepare a commit message base on information in the xml file and the augmented data"""
    xml = zip_to_xml(f)
    msg = (
        extract_long_name(xml)
        + '\n\n'
        + pypandoc.convert_text(augmented_data, to='markdown_github', format='html')
    )
    return msg


def commit_update(f, citation, message, repository):
    """
    Apply and commit the changes described in filename `f` to the given `repository`

    Parameters
    ----------
    f: str
        Filename of the zipped xml file
    citation: Citation
        Description of where and when this change took place
    repository: pygit2.Repository
        Repository to which this change should be applied
    """
    # remove /.git/ from path
    repo_path = path.dirname(path.dirname(repository.path))
    index = repository.index
    # The initial commit
    author = cabinet_sig(citation.date())
    # The path to the new / updated file rel. to the repo
    fname_md = path.basename(path.dirname(f)) + '.md'
    # Replace some chars
    fname_md = fname_md.replace('/', '_')
    md_path = path.join(repo_path, fname_md)
    with open(md_path, 'w') as f_md:
        xml = zip_to_xml(f)
        md = html_to_markdown(transform_gii_xml_to_html(xml))
        f_md.write(md)
    index.add(fname_md)
    index.write()
    try:
        head = repository.head
    except pygit2.GitError:
        head = None
    repository.create_commit(
        'refs/heads/master',  # the name of the reference to update
        author, author, message,
        # binary string representing the tree object ID
        index.write_tree(),
        # list of binary strings representing parents of the new commit
        [head.get_object().hex] if head is not None else []
    )


def augment_and_filter_files(files):
    """For each file, check if the relevant change was published in
    the BgBl I or II gazette. If so, try to find augmenting
    information about this change online.

    The augmenting information is returned as a string of valid and
    approriately cropped html. Files where the citation could not be
    established at all are filtered out.

    Parameter
    ---------
    files: list
        List of paths to zipped xml files

    Return
    ------
    list of tuple: [(filepath, citation, {str, None})]

    """
    from librelaws import xml_operations, online_lookups
    import concurrent.futures

    out = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=30) as executor:
        for f in files:
            xml = xml_operations.zip_to_xml(f)
            try:
                cit = xml_operations.Citation.from_xml(xml)
            except ValueError:
                # Skip files with no citation
                continue
            if cit.gazette not in ['BGBl I', 'BGBl II']:
                # Skip all the other gazettes for now
                continue
            try:
                cit.date()
            except TypeError:
                # Some parts of the dates were missing; skip those files
                continue
            out.append(
                [f, cit, executor.submit(online_lookups.search_bundestag_dip, cit.gazette, cit.year, cit.page)]
            )
    # Wait for lookups to finish...
    out = [(f, cit, fut.result()) for (f, cit, fut) in out]
    return sorted(out, key=lambda el: el[1].date())
