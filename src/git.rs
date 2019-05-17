use git2::{self, AnnotatedCommit, BranchType, Repository, Signature, Sort};

use crate::snapshot::Snapshot;
use crate::Result;


pub struct GitArchive {
    repo: Repository,
}

impl GitArchive {
    fn open(path: &str) -> Result<Self> {
        Ok(Self {
            repo: git2::Repository::init(path)?
        })
    }
    fn create_feature_branch(&self, snap: &Snapshot) -> Result<AnnotatedCommit> {
        // Find date
        let snap_time = snap.date()?;
        let mut revwalk = self.repo.revwalk().unwrap();
        revwalk.set_sorting(Sort::TIME);
        // Find first commit that is older than this snapshot. Thats where we branch
        let branch_point = revwalk
            .filter_map(|id| {
                let id = id.unwrap();
                let commit  = self.repo.find_commit(id).unwrap();
                if commit.time().seconds() < snap_time {
                    Some(commit)
                } else {
                    None
                }
            })
            .next()
            .unwrap();
        let branch = self.repo.branch(snap.key().unwrap(), &branch_point, false)
            .and_then(|b| self.repo.reference_to_annotated_commit(b.get()))?;
        let master = self.repo.head()
            .and_then(|r| self.repo.reference_to_annotated_commit(&r))?;
        // On merg conflict, always default to the (newer) versions in the mast branch
        let mut rebase_opts = git2::RebaseOptions::new();
        let mut merge_opts = git2::MergeOptions::new();
        merge_opts.file_favor(git2::FileFavor::Theirs);
        rebase_opts.merge_options(merge_opts);
        let mut rebase = self.repo.rebase(Some(&master), None, Some(&branch), Some(&mut rebase_opts))?;
        // find author
        let author = Signature::now("Mr. Rebase", "rebase@me.com")?;
        rebase
            .finish(&author)
            .unwrap();        
        // convert to md
        // determine target directory / delete old
        // [add figures]
        unimplemented!()
    }

    // pub fn apply_snapshot(&mut self, snap: &Snapshot) -> Result<()> {
    //     let commit = self.create_feature_branch(&snap).unwrap();
    //     let reference = self
    //         .repo
    //         .find_branch("master", BranchType::Local)
    //         .map(|b| b.into_reference())
    //         .unwrap();
    //     let master = self.repo.reference_to_annotated_commit(&reference).unwrap();

    //     let mut rebase = self
    //         .repo
    //         .rebase(Some(&master), None, Some(&commit), None)
    //         .unwrap();
    //     rebase
    //         .finish(&Signature::now("Mr. Rebase", "rebase@me.com").unwrap())
    //         .unwrap();
    //     Ok(())
    // }
}

#[cfg(test)]
mod tests {
    use super::*;
    const BEGDV_1_ZIP: &[u8] = include_bytes!("/home/christian/repos/librelaws/librelaws/src/test_files/xml.zip");
    #[test]
    fn rebase() {
        let snap = Snapshot::new("begdv_1").unwrap();
        snap.add_zipped_snapshot(BEGDV_1_ZIP, None).unwrap();
        let git = GitArchive::open("/home/christian/testtestgit/").unwrap();
        git.create_feature_branch(&snap).unwrap();
    }
}
