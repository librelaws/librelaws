#![allow(unused)]
//! Structures and functions for iterating over the locally available states
use std::path::{Path, PathBuf};

use failure::err_msg;
use tempfile::tempdir;

use crate::Result;

pub struct SnapshotArchive {
    root: PathBuf,
    snaps: Vec<Snapshot>,
}

impl SnapshotArchive {
    pub fn open(root: &str) -> Self {
        Self {
            root: root.into(),
            snaps: vec![],
        }
    }

    pub fn add_snapshot(&mut self, snap: Snapshot) {
        let date = chrono::Utc::today().format("%F").to_string();
        let to = self.root.join(&date).join(snap.key().unwrap());
        std::fs::create_dir_all(&to).unwrap();
        for entry in snap.snap_dir.read_dir().unwrap() {
            let file = entry.unwrap();
            let file_name = file.file_name();
            std::fs::rename(dbg!(file.path()), dbg!(to.join(file_name))).unwrap();
        }
        // // Move temp folder into this archive
        // std::fs::rename(snap.snap_dir, &dbg!(&to)).unwrap();
        self.snaps.push(Snapshot { snap_dir: to })
    }

    fn get(&self, key: &str) -> impl Iterator<Item = &Snapshot> {
        let key = key.to_string();
        self.snaps.iter().filter(move |snap| {
            if let Some(this_key) = snap.key() {
                this_key == key
            } else {
                false
            }
        })
    }
}

impl IntoIterator for SnapshotArchive {
    type Item = Snapshot;
    type IntoIter = IntoIter;
    fn into_iter(self) -> Self::IntoIter {
        Self::IntoIter {
            snaps_iter: self.snaps.into_iter(),
        }
    }
}

pub struct IntoIter {
    snaps_iter: std::vec::IntoIter<Snapshot>,
}

impl Iterator for IntoIter {
    type Item = Snapshot;

    fn next(&mut self) -> Option<Self::Item> {
        self.snaps_iter.next()
    }
}

pub struct Snapshot {
    snap_dir: PathBuf,
}

impl Snapshot {
    const PROCEEDINGS: &'static str = "proceedings.html";
    const ZIP: &'static str = "xml.zip";
    const ETAG: &'static str = "etag_gii.txt";

    pub fn new(key: &str) -> Result<Self> {
        let snap_dir = tempdir()?.into_path().join(key);
        std::fs::create_dir(&snap_dir)?;
        Ok(Self { snap_dir })
    }

    /// Date based on the inpection of the XML content
    pub fn date(&self) -> Result<i64> {
        use crate::gii::Entry;
        let entry = Entry::new(&self.zipped_snapshot()?)?;
        let (_, date) = entry.latest_status()?;
        Ok(date.and_hms(0,0,0).timestamp())
    }

    pub fn proceedings(&self) -> Option<String> {
        std::fs::read_to_string(self.snap_dir.join(Self::PROCEEDINGS)).ok()
    }

    pub fn add_proceedings(&self, buf: &[u8]) -> Result<()> {
        std::fs::write(self.snap_dir.join(Self::PROCEEDINGS), &buf).map_err(Into::into)
    }

    pub fn zipped_snapshot(&self) -> Result<Vec<u8>> {
        Ok(std::fs::read(self.snap_dir.join("xml.zip"))?)
    }

    pub fn add_zipped_snapshot(&self, buf: &[u8], etag: Option<&str>) -> Result<()> {
        std::fs::write(dbg!(self.snap_dir.join(Self::ZIP)), &buf)?;
        if let Some(etag) = etag {
            std::fs::write(self.snap_dir.join(Self::ETAG), etag)?;
        }
        Ok(())
    }

    pub fn key(&self) -> Option<&str> {
        self.snap_dir.file_name()?.to_str()
    }
}

/// Figure out the correct key for a snapshot based on the url from where it was downloaded
pub fn key_from_url<P: AsRef<Path>>(url: P) -> Result<String> {
    Ok(url
        .as_ref()
        .parent()
        .ok_or_else(|| err_msg("URL has no parent"))?
        .file_name()
        .ok_or_else(|| err_msg("URL has no parent"))?
        .to_str()
        .ok_or_else(|| err_msg("URL is not valid utf-8"))?
        .to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn do_stuff() {
        let archive = SnapshotArchive::open("");
        for _snap in archive {}
    }
}
