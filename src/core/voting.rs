use hashbrown::HashMap;

use crate::vdb::adapter::{DocId, ScoredDoc};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VoteClass {
    Strong,
    Weak,
    Noise,
}

#[derive(Debug, Clone)]
pub struct VoteRecord {
    pub doc_id: DocId,
    pub votes: u8,
    pub rank_score: f32,
    pub best_score: f32,
}

#[derive(Debug, Clone, Copy)]
struct VoteAggregate {
    votes: u8,
    rank_score: f32,
    best_score: f32,
}

pub fn merge_segment_results(segment_results: &[Vec<ScoredDoc>]) -> Vec<VoteRecord> {
    let mut aggregated = HashMap::<DocId, VoteAggregate>::new();

    for segment_result in segment_results {
        for (rank, (doc_id, score)) in segment_result.iter().enumerate() {
            let rank_score = 1.0f32 / (rank as f32 + 1.0);
            let entry = aggregated.entry(*doc_id).or_insert(VoteAggregate {
                votes: 0,
                rank_score: 0.0,
                best_score: f32::NEG_INFINITY,
            });
            entry.votes += 1;
            entry.rank_score += rank_score;
            entry.best_score = entry.best_score.max(*score);
        }
    }

    let mut records = aggregated
        .into_iter()
        .map(|(doc_id, agg)| VoteRecord {
            doc_id,
            votes: agg.votes,
            rank_score: agg.rank_score,
            best_score: agg.best_score,
        })
        .collect::<Vec<_>>();

    records.sort_by(|left, right| {
        right
            .votes
            .cmp(&left.votes)
            .then_with(|| {
                right
                    .rank_score
                    .partial_cmp(&left.rank_score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .then_with(|| {
                right
                    .best_score
                    .partial_cmp(&left.best_score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .then_with(|| left.doc_id.cmp(&right.doc_id))
    });

    records
}

pub fn classify_vote(votes: u8) -> VoteClass {
    match votes {
        3..=u8::MAX => VoteClass::Strong,
        2 => VoteClass::Weak,
        _ => VoteClass::Noise,
    }
}

pub fn select_survivor_ids(records: &[VoteRecord], limit: usize) -> Vec<DocId> {
    records
        .iter()
        .filter(|record| classify_vote(record.votes) != VoteClass::Noise)
        .take(limit)
        .map(|record| record.doc_id)
        .collect()
}
