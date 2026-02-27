// 목적:
// - 적재 작업의 핵심 파이프라인을 실행한다.
//
// 설명:
// - summary/page 노드 upsert와 summary 갱신 트리거를 수행한다.
//
// 디자인 패턴:
// - 명령 패턴(Command) 기반 분기.
//
// 참조:
// - src_rs/index/postgres_repo.rs

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::core::errors::{CoreError, CoreResult};
use crate::core::search_pipeline::PostgresConfigPayload;
use crate::index::postgres_repo::{IngestionPageNodeRecord, IngestionSummaryNodeRecord, PostgresRepository};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionSummaryNodePayload {
    pub node_id: String,
    pub document_id: String,
    pub path: String,
    pub summary_text: String,
    pub embedding: Vec<f32>,
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionPageNodePayload {
    pub node_id: String,
    pub parent_node_id: String,
    pub document_id: String,
    pub path: String,
    pub content: String,
    pub image_url: Option<String>,
    pub metadata: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionRequestPayload {
    pub operation: String,
    pub document_id: Option<String>,
    pub summary_nodes: Vec<IngestionSummaryNodePayload>,
    pub page_nodes: Vec<IngestionPageNodePayload>,
    pub postgres: PostgresConfigPayload,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionResultPayload {
    pub operation: String,
    pub upserted_summary_nodes: u64,
    pub upserted_page_nodes: u64,
    pub touched_summary_nodes: u64,
}

/// 적재 파이프라인을 실행한다.
pub async fn execute_ingestion(payload: IngestionRequestPayload) -> CoreResult<IngestionResultPayload> {
    if payload.operation.trim().is_empty() {
        return Err(CoreError::InvalidInput(
            "operation은 비어 있을 수 없습니다".to_string(),
        ));
    }

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

    match payload.operation.as_str() {
        "upsert_document" => {
            let summary_records = payload
                .summary_nodes
                .iter()
                .map(map_summary_record)
                .collect::<Vec<_>>();
            let page_records = payload
                .page_nodes
                .iter()
                .map(map_page_record)
                .collect::<Vec<_>>();

            let upserted_summary = repository.upsert_summary_nodes(&summary_records).await?;
            let upserted_pages = repository.upsert_page_nodes(&page_records).await?;

            Ok(IngestionResultPayload {
                operation: payload.operation,
                upserted_summary_nodes: upserted_summary,
                upserted_page_nodes: upserted_pages,
                touched_summary_nodes: 0,
            })
        }
        "upsert_pages" => {
            let page_records = payload
                .page_nodes
                .iter()
                .map(map_page_record)
                .collect::<Vec<_>>();
            let upserted_pages = repository.upsert_page_nodes(&page_records).await?;

            Ok(IngestionResultPayload {
                operation: payload.operation,
                upserted_summary_nodes: 0,
                upserted_page_nodes: upserted_pages,
                touched_summary_nodes: 0,
            })
        }
        "rebuild_summary_embeddings" => {
            let document_id = payload.document_id.clone().ok_or_else(|| {
                CoreError::InvalidInput("document_id가 필요합니다".to_string())
            })?;
            let touched = repository.touch_summary_nodes(&document_id).await?;

            Ok(IngestionResultPayload {
                operation: payload.operation,
                upserted_summary_nodes: 0,
                upserted_page_nodes: 0,
                touched_summary_nodes: touched,
            })
        }
        _ => Err(CoreError::InvalidInput(format!(
            "지원하지 않는 operation입니다: {}",
            payload.operation
        ))),
    }
}

fn map_summary_record(payload: &IngestionSummaryNodePayload) -> IngestionSummaryNodeRecord {
    IngestionSummaryNodeRecord {
        node_id: payload.node_id.clone(),
        document_id: payload.document_id.clone(),
        path: payload.path.clone(),
        summary_text: payload.summary_text.clone(),
        embedding: payload.embedding.clone(),
        metadata: payload.metadata.clone().unwrap_or(Value::Null),
    }
}

fn map_page_record(payload: &IngestionPageNodePayload) -> IngestionPageNodeRecord {
    IngestionPageNodeRecord {
        node_id: payload.node_id.clone(),
        parent_node_id: payload.parent_node_id.clone(),
        document_id: payload.document_id.clone(),
        path: payload.path.clone(),
        content: payload.content.clone(),
        image_url: payload.image_url.clone(),
        metadata: payload.metadata.clone().unwrap_or(Value::Null),
    }
}
