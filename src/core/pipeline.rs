use crate::core::{expansion, voting};
use crate::math::normalize;
use crate::vdb::adapter::{ScoredDoc, VdbAdapter};
use crate::vdb::query;

pub fn execute_search(
    adapter: &dyn VdbAdapter,
    query: &[f32],
    top_k: usize,
) -> Result<(Vec<u32>, Vec<f32>), String> {
    if top_k == 0 {
        return Err("top_k는 1 이상이어야 합니다".to_string());
    }
    if query.is_empty() {
        return Err("query는 비어 있을 수 없습니다".to_string());
    }
    if query.len() != adapter.dim() {
        return Err(format!(
            "쿼리 차원이 VDB 차원과 다릅니다: expected={}, actual={}",
            adapter.dim(),
            query.len()
        ));
    }

    let normalized_query = normalize::normalized_copy(query)
        .ok_or_else(|| "query 정규화에 실패했습니다 (0-벡터)".to_string())?;

    let segment_ranges = query::segment_ranges(normalized_query.len());
    let mut segment_results = Vec::<Vec<ScoredDoc>>::with_capacity(segment_ranges.len());
    for range in segment_ranges {
        let segment_query = query::build_segment_query(&normalized_query, range);
        segment_results.push(adapter.search(&segment_query, query::SEGMENT_TOP_K)?);
    }

    let vote_records = voting::merge_segment_results(&segment_results);
    let survivor_ids = voting::select_survivor_ids(&vote_records, query::SURVIVOR_COUNT);
    if survivor_ids.is_empty() {
        return Err("투표 규칙을 통과한 생존 후보가 없습니다".to_string());
    }

    let prf_query = expansion::build_prf_query(&normalized_query, &survivor_ids, adapter)?;
    let final_ranked = expansion::rerank_until_top_k(adapter, &prf_query, top_k)?;

    if final_ranked.is_empty() {
        return Err("최종 검색 결과가 비어 있습니다".to_string());
    }

    let (doc_ids, scores): (Vec<u32>, Vec<f32>) = final_ranked.into_iter().unzip();
    Ok((doc_ids, scores))
}
