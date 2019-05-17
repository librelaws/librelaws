use std::collections::HashMap;

use failure::{format_err, Error};
use futures::{future::Future, stream::Stream};
use libxml;
use libxslt;
use reqwest::r#async::{Client, ClientBuilder};

use crate::gazette::Gazette;

/// The Url which has to be hit to set the cookies for subsequent search queries
const COOKIE_LANDING: &str = "http://dipbt.bundestag.de/dip21.web/bt";
/// Url for search queries. Requires that the right cookies are present in the header
const SEARCH_URL: &str =
    "http://dipbt.bundestag.de/dip21.web/searchProcedures/advanced_search_list.do";

#[derive(Clone)]
pub struct BipClient(Client);

impl BipClient {
    /// Create a client which has the necessary cookies set for subsequent queries
    pub fn new() -> impl Future<Item = Self, Error = Error> {
        let client = ClientBuilder::new().cookie_store(true).build().unwrap();
        client
            .get(COOKIE_LANDING)
            .send()
            .map_err(Into::into)
            .map(|_| Self(client))
    }

    /// Fetch the specified proceedings
    pub fn fetch_proceedings(
        &self,
        gazette: &Gazette,
    ) -> impl Future<Item = String, Error = Error> {
        let (year, page) = (gazette.year().to_string(), gazette.page().to_string());
        let name = match gazette {
            Gazette::BGBl1 { .. } => "BGBl I",
            Gazette::BGBl2 { .. } => "BGBl II",
        };
        let query = prepare_query(name, &year, &page);
        self.0
            .post(SEARCH_URL)
            .form(&query)
            .send()
            .map_err(Into::into)
            // Concatenate the incoming bytes to the final body
            .and_then(|resp| {
                resp.into_body()
                    .concat2()
                    .map_err(Into::into)
                    .and_then(|chunk| String::from_utf8(chunk.to_vec()).map_err(Into::into))
                    .and_then(|s| crop_html(&s))
            })
    }
}

/// Prepare the query parameters as expected by bip
fn prepare_query<'a>(gazette: &'a str, year: &'a str, page: &'a str) -> HashMap<&'a str, &'a str> {
    [
        ("verkuendungsblatt", gazette),
        ("jahrgang", year),
        ("seite", page),
        // Unused parameters which are expected by the server...
        ("drsId", ""),
        ("plprId", ""),
        ("aeDrsId", ""),
        ("aePlprId", ""),
        ("vorgangId", ""),
        ("procedureContext", ""),
        ("vpId", ""),
        ("formChanged", "false"),
        ("promptUser", "false"),
        ("overrideChanged", "true"),
        ("javascriptActive", "yes"),
        ("personId", ""),
        ("personNachname", ""),
        ("prompt", "no"),
        ("anchor", ""),
        ("wahlperiodeaktualisiert", "false"),
        ("wahlperiode", ""),
        ("startDatum", ""),
        ("endDatum", ""),
        ("includeVorgangstyp", "UND"),
        ("nummer", ""),
        ("suchwort", ""),
        ("suchwortUndSchlagwort", "ODER"),
        ("schlagwort1", ""),
        ("linkSchlagwort2", "UND"),
        ("schlagwort2", ""),
        ("linkSchlagwort3", "UND"),
        ("schlagwort3", ""),
        ("unterbegriffsTiefe", "0"),
        ("sachgebiet", ""),
        ("includeKu", "UND"),
        ("ressort", ""),
        ("nachname", ""),
        ("vorname", ""),
        ("heftnummer", ""),
        ("verkuendungStartDatum", ""),
        ("verkuendungEndDatum", ""),
        ("btBrBeteiligung", "alle"),
        ("gestaOrdnungsnummer", ""),
        ("beratungsstand", ""),
        ("signaturParlamentsarchiv", ""),
        ("method", "Suchen"),
    ]
    .iter()
    .map(|el| el.to_owned())
    .collect::<HashMap<_, _>>()
}

fn crop_html(html: &str) -> Result<String, Error> {
    libxml::parser::Parser::default_html()
        .parse_string(html)
        .map(|doc| {
            let mut xsl = libxslt::parser::parse_file(
                "/home/christian/repos/librelaws/librelaws/librelaws/assets/crop_bip_html.xsl",
            )
            .unwrap();
            xsl.transform(&doc).unwrap().to_string(true)
        })
        .map_err(|e| format_err!("{:?}", e))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tokio;

    #[test]
    fn bad_gazette() {
        let future = BipClient::new().and_then(|client| {
            client.fetch_proceedings(&Gazette::BGBl1 {
                year: 1998,
                page: 1666,
            })
        });

        let mut rt = tokio::runtime::current_thread::Runtime::new().expect("new rt");
        let html = rt.block_on(future).unwrap();
        fs::write("./bad.html", html).unwrap();
    }

    #[test]
    fn fetch_bip() {
        let future = BipClient::new().and_then(|client| {
            client.fetch_proceedings(&Gazette::BGBl1 {
                year: 2019,
                page: 54,
            })
        });

        let mut rt = tokio::runtime::current_thread::Runtime::new().expect("new rt");
        let html = rt.block_on(future).unwrap();
        fs::write("./bip_result.html", html).unwrap();
    }
}
