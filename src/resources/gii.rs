use std::collections::HashMap;
use std::io::Read;
use std::path::Path;

use chrono::{self, Datelike, NaiveDate};
use failure::{format_err, Error};
use futures::{Future, Stream};
use glob::glob;
use libxml;
use log::debug;
use regex;
use reqwest::{header, r#async::Client};
use url::Url;
use zip::ZipArchive;

use crate::gazette::Gazette;

const ROOT: &str = "http://www.gesetze-im-internet.de/";
const TOC: &str = "gii-toc.xml";

pub struct GiiClient {
    client: Client,
    dirname_etag_map: HashMap<String, String>,
}

pub struct Entry {
    //    path: PathBuf,
    xml: String,
}

impl Entry {
    pub fn new(buf: &[u8]) -> Result<Self, Error> {
        let xml = zip_to_xml_string(&buf)?;
        Ok(Self { xml })
    }

    pub fn latest_status(&self) -> Result<(Gazette, NaiveDate), Error> {
        let doc = libxml::parser::Parser::default()
            .parse_string(&self.xml)
            .map_err(|e| format_err!("Invalid XML: {:?}", e))?;
        let root = doc
            .get_root_element()
            .ok_or_else(|| format_err!("Could not set ROOT node"))?;
        let all_comments = root
            .findnodes("//standangabe/standkommentar")
            .map_err(|e| format_err!("XPath query failed: {:?}", e))?
            .iter()
            .map(|node| node.get_content())
            .collect::<Vec<_>>();
        let mut parsed_comments: Vec<_> = all_comments
            .iter()
            .filter_map(|com| parse_status_comment(com))
            .collect();
        parsed_comments.as_mut_slice().sort_by(|a, b| a.1.cmp(&b.1));
        parsed_comments
            .pop()
            .ok_or_else(|| format_err!("Failed to parse any status comments"))
    }
}

pub enum GiiResponse {
    Update {
        url: String,
        buf: Vec<u8>,
        etag: String,
    },
    Unchanged,
}

impl GiiClient {
    pub fn new<P: AsRef<Path>>(archive_folder: P) -> Result<Self, Error> {
        let paths = glob(archive_folder.as_ref().join("**/*.zip").to_str().unwrap())?;
        let dirname_etag_map = paths
            .filter_map(Result::ok)
            .filter_map(|p| {
                let dir_name = folder_name_from_url(p.to_str()?);
                let etag = p
                    .file_name()?
                    .to_str()?
                    .trim_end_matches(".zip")
                    .to_string();
                Some((dir_name.to_string(), etag))
            })
            .collect();
        Ok(Self {
            client: Client::new(),
            dirname_etag_map,
        })
    }

    pub fn get_if_newer(&self, url: &str) -> impl Future<Item = GiiResponse, Error = Error> {
        let mut req = self.client.get(url);
        let dir_name = folder_name_from_url(url);
        if let Some(etag) = self.dirname_etag_map.get(&dir_name) {
            req = req.header(header::IF_NONE_MATCH, format!("\"{}\"", etag.clone()));
            debug!("Set if-none-match header: {:?}", req);
        }
        let url = url.to_string();
        req.send()
            .and_then(|resp| resp.error_for_status())
            .and_then(move |resp| {
                let etag = resp
                    .headers()
                    .get(header::ETAG)
                    .expect("Response set no etag")
                    .to_str()
                    .unwrap()
                    .to_string();
                resp.into_body()
                    .concat2()
                    .map(move |chunk| GiiResponse::Update {
                        url,
                        etag,
                        buf: chunk.to_vec(),
                    })
            })
            .map_err(Into::into)
    }
}

fn folder_name_from_url<P: AsRef<Path>>(url: P) -> String {
    url.as_ref()
        .parent()
        .unwrap()
        .file_name()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string()
}

/// Get the links to all laws currently online at `gesetze-im-internet.de`
pub(crate) fn get_links() -> impl Future<Item = Vec<String>, Error = Error> {
    Client::new()
        .get(Url::parse(ROOT).unwrap().join(TOC).unwrap())
        .send()
        .map_err(Into::into)
        // Concatenate the incoming bytes to the final body
        .and_then(|resp| {
            resp.into_body()
                .concat2()
                .map_err(Into::into)
                .and_then(|chunk| String::from_utf8(chunk.to_vec()).map_err(Into::into))
                .and_then(|s| {
                    let doc = libxml::parser::Parser::default()
                        .parse_string(&s)
                        .map_err(|e| format_err!("Invalid XML: {:?}", e))?;
                    // TODO: File bug report. `get_root_element` only works if we assign `doc`
                    let root = doc
                        .get_root_element()
                        .ok_or_else(|| format_err!("Could not set ROOT node"))?;

                    root.findnodes("//link")
                        .map_err(|e| format_err!("XPath query failed: {:?}", e))?
                        .iter()
                        .map(|node| Ok(node.get_content()))
                        .collect::<Result<Vec<_>, _>>()
                })
        })
}

fn find_latest_status_comment(xml: &str) -> Result<(Gazette, NaiveDate), Error> {
    let doc = libxml::parser::Parser::default()
        .parse_string(&xml)
        .map_err(|e| format_err!("Invalid XML: {:?}", e))?;
    let root = doc
        .get_root_element()
        .ok_or_else(|| format_err!("Could not set ROOT node"))?;
    let all_comments = root
        .findnodes("//standangabe/standkommentar")
        .map_err(|e| format_err!("XPath query failed: {:?}", e))?
        .iter()
        .map(|node| node.get_content())
        .collect::<Vec<_>>();
    let mut parsed_comments: Vec<_> = all_comments
        .iter()
        .filter_map(|com| parse_status_comment(com))
        .collect();
    parsed_comments.as_mut_slice().sort_by(|a, b| a.1.cmp(&b.1));
    parsed_comments
        .pop()
        .ok_or_else(|| format_err!("Failed to parse any status comments"))
}

fn zip_to_xml_string(bytes: &[u8]) -> Result<String, Error> {
    let reader = std::io::Cursor::new(bytes);
    let mut archive = ZipArchive::new(reader)?;
    let mut buffers: Vec<String> = (0..archive.len())
        .filter_map(|i| {
            let mut file = archive.by_index(i).unwrap();
            if file.name().contains(".xml") {
                let mut s = String::default();
                file.read_to_string(&mut s).unwrap();
                Some(s)
            } else {
                None
            }
        })
        .collect();
    if buffers.len() != 1 {
        return Err(format_err!("Expected exactly one xml file in zip archive"));
    } else {
        return Ok(buffers.swap_remove(0));
    }
}

fn parse_status_comment(s: &str) -> Option<(Gazette, chrono::NaiveDate)> {
    let re = regex::Regex::new(r"\w\.\s(\d{1,2})\.\s{0,1}(\d{1,2})\.(\d{4})\s(\w+)\s(\d+)").ok()?;
    let cap = re.captures(s)?;
    let full_date = chrono::NaiveDate::from_ymd(
        cap[3].parse().ok()?,
        cap[2].parse().ok()?,
        cap[1].parse().ok()?,
    );
    let page = cap[5].parse().ok()?;
    let gazette = match &cap[4] {
        "I" => Gazette::BGBl1 {
            year: full_date.year(),
            page,
        },
        "II" => Gazette::BGBl2 {
            year: full_date.year(),
            page,
        },
        _ => return None,
    };
    Some((gazette, full_date))
}

#[cfg(test)]
mod tests {
    use super::*;
    use futures::stream::iter_ok;
    use tokio;

    #[test]
    fn fetch_links_gii() {
        env_logger::init();
        let future = get_links();
        let mut rt = tokio::runtime::current_thread::Runtime::new().expect("new rt");
        let links = rt.block_on(future).unwrap();
        assert!(links.len() > 0);
    }

    #[test]
    fn extract_dates() {
        // Strings not working yet
        let not_recognized_yet = [
            "Konstitutive Neufassung gem. Art. I V v. 13.4.1966, in Kraft getreten am 4.5.1966",
            "Berichtigung vom 2.10.2017 I 3527 ist berücksichtigt",
        ];
        for s in &not_recognized_yet {
            assert_eq!(parse_status_comment(s), None);
        }

        // Strings which should work:
        let examples = [
            "Ersetzt V v. 7.9.1954 I 271",
            // Whitespace in dates
            "Zuletzt geändert durch Art. 4 Abs. 11 G v. 22. 9.2005 I 280",
            "Geändert durch § 8 V v. 31. 3.1966 I 199",
            "Zuletzt geändert durch Art. 1 V v. 27.4.2017 I 980",
            "Änderung durch Art. 1 V v. 18.4.2019 I 487 (Nr. 13) textlich nachgewiesen, dokumentarisch noch nicht abschließend bearbeitet",
        ];
        for ex in &examples {
            parse_status_comment(ex).unwrap();
        }
    }

    #[test]
    fn setup_client() {
        use crate::resources::bip::BipClient;
        let client = GiiClient::new("/home/christian/groundzero").unwrap();
        let mut rt = tokio::runtime::current_thread::Runtime::new().expect("new rt");
        let bip_client = rt.block_on(BipClient::new()).unwrap();
        let future = get_links().and_then(move |links| {
            iter_ok(links.into_iter().take(10))
                .and_then(move |l| client.get_if_newer(&l))
                .and_then(|resp| {
                    if let GiiResponse::Update { url, buf, etag: _ } = resp {
                        zip_to_xml_string(&buf).map(|s| (url, s))
                    } else {
                        panic!()
                    }
                })
                .filter_map(|(link, xml)| {
                    find_latest_status_comment(&xml)
                        .map(|(gazette, _date)| (link, gazette, xml))
                        .ok()
                })
                .map(move |(link, gazette, xml)| {
                    bip_client
                        .fetch_proceedings(&gazette)
                        .map(move |proceeding| (link.to_string(), gazette, proceeding, xml))
                })
                .buffer_unordered(30)
                .for_each(|(link, state, proceeding, _xml)| {
                    if proceeding.len() < 100 {
                        dbg!((&link, state));
                    }
                    Ok(())
                })
        });
        rt.block_on(future).unwrap();
    }
}
