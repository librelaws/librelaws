#[derive(Debug, PartialEq)]
pub enum Gazette {
    BGBl1 { year: i32, page: u32 },
    BGBl2 { year: i32, page: u32 },
}

impl Gazette {
    pub fn year(&self) -> i32 {
        match self {
            Gazette::BGBl1 { year, .. } | Gazette::BGBl2 { year, .. } => *year,
        }
    }
    pub fn page(&self) -> u32 {
        match self {
            Gazette::BGBl1 { page, .. } | Gazette::BGBl2 { page, .. } => *page,
        }
    }
}
