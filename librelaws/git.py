import pygit2
from datetime import datetime, date


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


def commit_entry(entry, repo_path="___test_repo___"):
    repo = pygit2.init_repository(repo_path)
    index = repo.index

    # The initial commit
    author = cabinet_sig(entry['bgbl'].date)

    # The path to the new / updated file rel. to the repo
    new_file = entry['abbrev'] + '.md'
    # Replace some chars
    new_file = new_file.replace('/', '_')
    with open(path.join(repo_path, new_file), 'w') as f:
        f.write(entry['md'])
    index.add(new_file)
    index.write()
    
    try:
        head = repo.head
    except pygit2.GitError:
        head = None
    
    repo.create_commit(
        'refs/heads/master', # the name of the reference to update
        author, author, entry['msg'],
        # binary string representing the tree object ID
        index.write_tree(),
        # list of binary strings representing parents of the new commit
        [head.get_object().hex] if head is not None else []
    )
# for entry in entries[:]:    
#     commit_entry(entry)
