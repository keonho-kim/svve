use std::cmp::Ordering;

use crate::vdb::adapter::ScoredDoc;

pub fn sort_desc_take(scored: &mut Vec<ScoredDoc>, top_k: usize) {
    scored.sort_by(compare_scored_doc);
    if scored.len() > top_k {
        scored.truncate(top_k);
    }
}

fn compare_scored_doc(left: &ScoredDoc, right: &ScoredDoc) -> Ordering {
    right
        .1
        .partial_cmp(&left.1)
        .unwrap_or(Ordering::Equal)
        .then_with(|| left.0.cmp(&right.0))
}
