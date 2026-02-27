// 목적:
// - 검색 작업의 핵심 파이프라인을 실행한다.
//
// 설명:
// - pgvector 엔트리 탐색 -> ltree 하위 페이지 확장 -> HTTP 필터링 -> top-k 절삭 순서로 처리한다.
//
// 디자인 패턴:
// - 파이프라인(Pipeline).
//
// 참조:
// - src_rs/index/postgres_repo.rs
// - src_rs/core/filter_http.rs

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::time::Instant;

use crate::core::errors::{CoreError, CoreResult};
use crate::core::filter_http::{
    FilterCandidateInput, FilterDecision, FilterHttpClient, FilterHttpConfigPayload,
};
use crate::index::postgres_repo::{PageNodeRecord, PostgresRepository};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PostgresConfigPayload {
    pub dsn: String,
    pub summary_table: String,
    pub page_table: String,
    pub pool_min: u32,
    pub pool_max: u32,
    pub connect_timeout_ms: u64,
    pub statement_timeout_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchRequestPayload {
    pub job_id: String,
    pub question: String,
    pub query_embedding: Vec<f32>,
    pub top_k: usize,
    pub entry_limit: usize,
    pub page_limit: usize,
    pub worker_concurrency: usize,
    pub postgres: PostgresConfigPayload,
    pub filter_http: FilterHttpConfigPayload,
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchCandidatePayload {
    pub node_id: String,
    pub path: String,
    pub score: f32,
    pub content: String,
    pub image_url: Option<String>,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchMetricsPayload {
    pub entry_count: usize,
    pub page_count: usize,
    pub kept_count: usize,
    pub elapsed_ms: u128,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResultPayload {
    pub job_id: String,
    pub candidates: Vec<SearchCandidatePayload>,
    pub metrics: SearchMetricsPayload,
}

/// 검색 파이프라인을 실행한다.
pub async fn execute_search(payload: SearchRequestPayload) -> CoreResult<SearchResultPayload> {
    validate_payload(&payload)?;

    let started = Instant::now();
    let repository = PostgresRepository::new(
        &payload.postgres.dsn,
        &payload.postgres.summary_table,
        &payload.postgres.page_table,
        payload.postgres.pool_min,
        payload.postgres.pool_max,
        payload.postgres.connect_timeout_ms,
        payload.postgres.statement_timeout_ms,
    )
    .await?;

    let entry_records = repository
        .search_summary_nodes(&payload.query_embedding, payload.entry_limit)
        .await?;

    let mut parent_score_map = HashMap::<String, f32>::new();
    let mut expanded_pages = Vec::<PageNodeRecord>::new();
    for entry in &entry_records {
        parent_score_map.insert(entry.node_id.clone(), entry.score);
        let pages = repository
            .fetch_pages_under_path(&entry.path, payload.page_limit)
            .await?;
        expanded_pages.extend(pages);
    }

    let filter_client = FilterHttpClient::new(payload.filter_http.clone())?;
    let filter_inputs = expanded_pages
        .iter()
        .map(|page| FilterCandidateInput {
            node_id: page.node_id.clone(),
            content: page.content.clone(),
        })
        .collect::<Vec<_>>();

    let filter_decisions = filter_client
        .filter_candidates(&payload.question, &filter_inputs, payload.worker_concurrency)
        .await?;

    let decision_map = filter_decisions
        .into_iter()
        .map(|decision| (decision.node_id.clone(), decision))
        .collect::<HashMap<_, _>>();

    let mut kept = expanded_pages
        .into_iter()
        .filter_map(|page| to_candidate(page, &parent_score_map, &decision_map))
        .collect::<Vec<_>>();

    kept.sort_by(|left, right| {
        right
            .score
            .partial_cmp(&left.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| left.path.cmp(&right.path))
    });

    if kept.len() > payload.top_k {
        kept.truncate(payload.top_k);
    }

    let elapsed = started.elapsed().as_millis();
    let metrics = SearchMetricsPayload {
        entry_count: entry_records.len(),
        page_count: filter_inputs.len(),
        kept_count: kept.len(),
        elapsed_ms: elapsed,
    };

    Ok(SearchResultPayload {
        job_id: payload.job_id,
        candidates: kept,
        metrics,
    })
}

fn to_candidate(
    page: PageNodeRecord,
    parent_score_map: &HashMap<String, f32>,
    decision_map: &HashMap<String, FilterDecision>,
) -> Option<SearchCandidatePayload> {
    let decision = decision_map.get(&page.node_id)?;
    if !decision.keep {
        return None;
    }

    let score = parent_score_map
        .get(&page.parent_node_id)
        .copied()
        .unwrap_or(0.0)
        .clamp(0.0, 1.0);

    Some(SearchCandidatePayload {
        node_id: page.node_id,
        path: page.path,
        score,
        content: page.content,
        image_url: page.image_url,
        reason: decision.reason.clone(),
    })
}

fn validate_payload(payload: &SearchRequestPayload) -> CoreResult<()> {
    if payload.job_id.trim().is_empty() {
        return Err(CoreError::InvalidInput(
            "job_id는 비어 있을 수 없습니다".to_string(),
        ));
    }

    if payload.question.trim().is_empty() {
        return Err(CoreError::InvalidInput(
            "question은 비어 있을 수 없습니다".to_string(),
        ));
    }

    if payload.query_embedding.is_empty() {
        return Err(CoreError::InvalidInput(
            "query_embedding은 최소 1개 이상이어야 합니다".to_string(),
        ));
    }

    if payload.top_k == 0 {
        return Err(CoreError::InvalidInput(
            "top_k는 1 이상이어야 합니다".to_string(),
        ));
    }

    if payload.entry_limit == 0 {
        return Err(CoreError::InvalidInput(
            "entry_limit은 1 이상이어야 합니다".to_string(),
        ));
    }

    if payload.page_limit == 0 {
        return Err(CoreError::InvalidInput(
            "page_limit은 1 이상이어야 합니다".to_string(),
        ));
    }

    if payload.worker_concurrency == 0 {
        return Err(CoreError::InvalidInput(
            "worker_concurrency는 1 이상이어야 합니다".to_string(),
        ));
    }

    Ok(())
}
