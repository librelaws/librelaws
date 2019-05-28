use git2::{self, AnnotatedCommit, Repository, Signature, Sort};

use crate::snapshot::Snapshot;
use crate::Result;

pub struct GitArchive {
    repo: Repository,
}

impl GitArchive {
    fn open(path: &str) -> Result<Self> {
        let repo = git2::Repository::init(path)?;

        // First use the config to initialize a commit signature for the user.
        let sig = Signature::new("First commit", "Blub", &git2::Time::new(0, 0))?;

        // Now let's create an empty tree for this commit
        let tree_id = {
            let mut index = repo.index()?;
            // Outside of this example, you could call index.add_path()
            // here to put actual files into the index. For our purposes, we'll
            // leave it empty for now.
            index.write_tree()?
        };
        {
            let tree = repo.find_tree(tree_id)?;

            // Ready to create the initial commit.
            //
            // Normally creating a commit would involve looking up the current HEAD
            // commit and making that be the parent of the initial commit, but here this
            // is the first commit so there will be no parent.
            if let Err(e) = repo.commit(Some("HEAD"), &sig, &sig, "Initial commit blub", &tree, &[])
            {
                dbg!(e);
            };
        }
        Ok(Self { repo })
    }

    /// Find the first commit just before `instance`
    fn find_branch_point(&self, instance: i64) -> Result<git2::Commit> {
        let mut revwalk = self.repo.revwalk()?;
        revwalk.set_sorting(Sort::TIME);
        revwalk.push_head()?;
        // Find first commit that is older than this snapshot. Thats where we branch
        let branch_point = revwalk
            .filter_map(|id| {
                let id = dbg!(id.unwrap());
                let commit = self.repo.find_commit(id).unwrap();
                if commit.time().seconds() < instance {
                    Some(commit)
                } else {
                    None
                }
            })
            .next()
            .unwrap();
        Ok(branch_point)
    }
        
    fn create_feature_branch(&self, snap: &Snapshot) -> Result<AnnotatedCommit> {
        // Find date
        let snap_time = snap.date()?;
        let branch_point = self.find_branch_point(snap_time)?;
        dbg!((&branch_point, self.repo.head()?.peel_to_commit()?));
        let branch_name = snap.key().unwrap();
        let mut branch = self.repo.branch(branch_name, &branch_point, false)?;
        let branch_annot = self.repo.reference_to_annotated_commit(branch.get())?;
        let master = self
            .repo
            .head()
            .and_then(|r| self.repo.reference_to_annotated_commit(&r))?;
        // Checkout the new branch
        let branch_ref = branch.get().name().unwrap();
        self.repo.set_head(branch_ref)?;
        self.repo.checkout_head(None)?;
        // find author
        let sig = Signature::now("Mr. Rebase", "rebase@me.com")?;
        // convert to md
        std::fs::write("/home/christian/testtestgit/test.txt", b"testtest")?;
        let mut index = self.repo.index()?;
        index.add_path(std::path::Path::new("test.txt"))?;
        index.write().unwrap();
        // Commit changes
        let parent = self.repo.head()?.peel_to_commit()?;
        // let tree = parent.tree()?;
        let tree = self.repo.find_tree(index.write_tree()?)?;
        self.repo
            .commit(Some("HEAD"), &sig, &sig, "second", &tree, &[&parent])
            .unwrap();
        index.write_tree()?;
        dbg!(self.repo.status_file(std::path::Path::new("test.txt"))?);
        for entry in index.iter() {
            dbg!(std::str::from_utf8(&entry.path)?);
        }
        // Rebase everything
        // On merge conflict, always default to the (newer) versions in the mast branch
        let mut rebase_opts = git2::RebaseOptions::new();
        let mut merge_opts = git2::MergeOptions::new();
        merge_opts.file_favor(git2::FileFavor::Theirs);
        rebase_opts.merge_options(merge_opts);
        let mut rebase = self.repo.rebase(
            Some(&master),
            None,
            Some(&branch_annot),
            Some(&mut rebase_opts),
        )?;
        rebase.finish(&sig).unwrap();
        // Usually, master should now include the latest commit, but
        // it might be that we actually were working on the latest
        // commit in which case the rebase did nothing. We force
        // rename to master here to fix that
       branch.rename("master", true)?;

        self.repo.reset(
            &self.repo.head()?.peel(git2::ObjectType::Any)?,
            git2::ResetType::Hard,
            None,
        )?;

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
    const BEGDV_1_ZIP: &[u8] =
        include_bytes!("/home/christian/repos/librelaws/librelaws/src/test_files/xml.zip");
    #[test]
    fn rebase() {
        let snap = Snapshot::new("begdv_1").unwrap();
        snap.add_zipped_snapshot(BEGDV_1_ZIP, None).unwrap();
        let _ = std::fs::remove_dir_all("/home/christian/testtestgit/.");
        let git = GitArchive::open("/home/christian/testtestgit/").unwrap();

        git.create_feature_branch(&snap).unwrap();
    }
}
