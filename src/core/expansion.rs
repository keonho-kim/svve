use hashbrown::HashMap;
use std::collections::HashSet;

use crate::math::{normalize, topk};
use crate::vdb::adapter::{DocId, ScoredDoc, VdbAdapter};
use crate::vdb::{fetch, query};

const EARLY_STOP_JACCARD_THRESHOLD: f32 = 0.95;
const EARLY_STOP_SCORE_IMPROVEMENT_THRESHOLD: f32 = 0.005;
const EARLY_STOP_STABLE_ROUNDS: usize = 2;

pub fn build_prf_query(
    original_query: &[f32],
    survivors: &[DocId],
    adapter: &dyn VdbAdapter,
) -> Result<Vec<f32>, String> {
    if survivors.is_empty() {
        return Err("PRF를 위한 생존 문서가 비어 있습니다".to_string());
    }

    let survivor_vectors = fetch::fetch_vectors(adapter, survivors)?;
    let center = fetch::centroid(&survivor_vectors, original_query.len())?;

    let mut expanded = Vec::with_capacity(original_query.len());
    for (query_value, center_value) in original_query.iter().zip(center.iter()) {
        expanded
            .push(query::PRF_ALPHA * *query_value + (1.0f32 - query::PRF_ALPHA) * *center_value);
    }

    normalize::normalized_copy(&expanded)
        .ok_or_else(|| "PRF 보정 쿼리 정규화에 실패했습니다 (0-벡터)".to_string())
}

pub fn rerank_until_top_k(
    adapter: &dyn VdbAdapter,
    prf_query: &[f32],
    top_k: usize,
) -> Result<Vec<ScoredDoc>, String> {
    if top_k == 0 {
        return Ok(Vec::new());
    }

    let base_limit = top_k.max(query::SEGMENT_TOP_K);
    let mut merged = HashMap::<DocId, f32>::new();
    let mut prev_top_ids: Option<HashSet<DocId>> = None;
    let mut prev_top_score_sum: Option<f32> = None;
    let mut stable_rounds = 0usize;

    for round in 1..=query::MAX_REFINEMENT_ROUNDS {
        let limit = base_limit.saturating_mul(round);
        let round_hits = adapter.search(prf_query, limit)?;
        let round_hit_count = round_hits.len();

        for (doc_id, score) in round_hits {
            let entry = merged.entry(doc_id).or_insert(score);
            if score > *entry {
                *entry = score;
            }
        }

        let current_top = top_k_from_merged(&merged, top_k);
        let current_top_ids = current_top
            .iter()
            .map(|(doc_id, _)| *doc_id)
            .collect::<HashSet<_>>();
        let current_top_score_sum = current_top.iter().map(|(_, score)| *score).sum::<f32>();

        if let (Some(prev_ids), Some(prev_score_sum)) = (prev_top_ids.as_ref(), prev_top_score_sum)
        {
            let jaccard = jaccard_similarity(prev_ids, &current_top_ids);
            let improvement = relative_score_improvement(prev_score_sum, current_top_score_sum);

            if jaccard >= EARLY_STOP_JACCARD_THRESHOLD
                && improvement <= EARLY_STOP_SCORE_IMPROVEMENT_THRESHOLD
            {
                stable_rounds += 1;
            } else {
                stable_rounds = 0;
            }
        }

        prev_top_ids = Some(current_top_ids);
        prev_top_score_sum = Some(current_top_score_sum);

        if round_hit_count < limit {
            break;
        }

        if merged.len() >= top_k && stable_rounds >= EARLY_STOP_STABLE_ROUNDS {
            break;
        }
    }

    let mut reranked = merged.into_iter().collect::<Vec<ScoredDoc>>();
    topk::sort_desc_take(&mut reranked, top_k);
    Ok(reranked)
}

fn top_k_from_merged(merged: &HashMap<DocId, f32>, top_k: usize) -> Vec<ScoredDoc> {
    let mut ranked = merged
        .iter()
        .map(|(doc_id, score)| (*doc_id, *score))
        .collect();
    topk::sort_desc_take(&mut ranked, top_k);
    ranked
}

fn jaccard_similarity(left: &HashSet<DocId>, right: &HashSet<DocId>) -> f32 {
    if left.is_empty() && right.is_empty() {
        return 1.0;
    }

    let intersection = left.intersection(right).count() as f32;
    let union = left.union(right).count() as f32;
    if union <= f32::EPSILON {
        return 1.0;
    }
    intersection / union
}

fn relative_score_improvement(previous_sum: f32, current_sum: f32) -> f32 {
    let denom = previous_sum.abs().max(1e-6);
    ((current_sum - previous_sum) / denom).abs()
}
