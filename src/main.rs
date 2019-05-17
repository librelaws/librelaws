use std::path::Path;

use clap::{App, Arg};
use failure::Error;
use futures::{stream::iter_ok, Future, Stream};
use tokio::runtime::current_thread::Runtime;

mod gazette;
mod git;
pub mod resources;
mod snapshot;
use resources::{
    bip::BipClient,
    gii::{self, get_links, GiiClient},
};

pub type Result<T> = std::result::Result<T, Error>;

fn main() {
    try_main().unwrap();
}

fn try_main() -> Result<()> {
    let matches = App::new("Librelaws")
        .version("0.1")
        .author("Christian Bourjau <christianb@posteo.de>")
        .about("Convert German laws into a git repository")
        .arg(
            Arg::with_name("ARCHIVE")
                .short("x")
                .long("xml-archive")
                .value_name("PATH")
                .required(true)
                .help("Path to folder holding downloaded xml files"),
        )
        // .arg(
        //     Arg::with_name("GIT_FOLDER")
        //         .long("output-git")
        //         .short("o")
        //         .help("Path to directory of the output git repository")
        //         .required(true)
        //         .value_name("PATH"),
        // )
        // .arg(Arg::with_name("USE_ARCHIVE_ORG")
        //      .long("use-archive-org")
        //      .help("Include internet archive as a resource")
        // )
        .arg(
            Arg::with_name("v")
                .short("v")
                .multiple(true)
                .help("Sets the level of verbosity"),
        )
        .get_matches();

    let archive = Path::new(matches.value_of("ARCHIVE").unwrap());
    let _new_files = download_gii(&archive)?;
    download_bip_proceedings(&archive)?;
    Ok(())
}

/// Update the existing archive using gesetze-im-internet.de
fn download_gii<P: AsRef<Path>>(path: &P) -> Result<()> {
    std::fs::create_dir_all(&path)?;
    let client = GiiClient::new(&path)?;
    let mut rt = Runtime::new()?;
    let links = rt.block_on(get_links())?;
    let future = iter_ok(links.iter().take(10))
        .and_then(|ref url| client.get_if_newer(&url))
        .map(|args| Ok(args))
        .buffer_unordered(30)
        .filter_map(|resp| {
            if let gii::GiiResponse::Update { url, buf, etag } = resp {
                let key = snapshot::key_from_url(&url).unwrap();
                let snap = snapshot::Snapshot::new(&key).unwrap();
                snap.add_zipped_snapshot(&buf, Some(&etag)).unwrap();
                Some(snap)
            } else {
                None
            }
        })
        .collect();
    let updates = rt.block_on(future)?;
    let mut archive = snapshot::SnapshotArchive::open(&path.as_ref().to_str().unwrap());
    for snap in updates.into_iter() {
        archive.add_snapshot(snap);
    }
    Ok(())
}

fn download_bip_proceedings<P: AsRef<Path>>(path: P) -> Result<()> {
    let mut rt = Runtime::new()?;
    let bip_client = rt.block_on(BipClient::new()).unwrap();
    let archive = snapshot::SnapshotArchive::open(&path.as_ref().to_str().unwrap());
    for snap in archive.into_iter() {
        let entry = gii::Entry::new(&snap.zipped_snapshot()?)?;
        let (gazette, _date) = entry.latest_status()?;
        let fut = bip_client
            .fetch_proceedings(&gazette)
            .and_then(move |proc| snap.add_proceedings(proc.as_bytes()))
            .map_err(|e| eprintln!("{}", e));
        rt.spawn(fut);
    }
    Ok(rt.run()?)
}
