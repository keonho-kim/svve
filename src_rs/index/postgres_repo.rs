// 목적:
// - PostgreSQL 기반 저장소 접근을 담당한다.
//
// 설명:
// - summary/page 조회와 upsert를 제공한다.
// - 테이블명은 실행 시 검증해 SQL 주입 위험을 줄인다.
//
// 디자인 패턴:
// - 저장소 패턴(Repository Pattern).
//
// 참조:
// - src_rs/index/sql.rs
// - src_rs/core/search_pipeline.rs

use serde_json::Value;
use sqlx::postgres::{PgPoolOptions, PgRow};
use sqlx::{PgPool, Row};

use crate::core::errors::{CoreError, CoreResult};
use crate::index::sql::{to_pgvector_literal, validate_identifier};

#[derive(Debug, Clone)]
pub struct SummaryNodeRecord {
    pub node_id: String,
    pub path: String,
    pub score: f32,
}

#[derive(Debug, Clone)]
pub struct PageNodeRecord {
    pub node_id: String,
    pub parent_node_id: String,
    pub path: String,
    pub content: String,
    pub image_url: Option<String>,
}

#[derive(Debug, Clone)]
pub struct IngestionSummaryNodeRecord {
    pub node_id: String,
    pub document_id: String,
    pub path: String,
    pub summary_text: String,
    pub embedding: Vec<f32>,
    pub metadata: Value,
}

#[derive(Debug, Clone)]
pub struct IngestionPageNodeRecord {
    pub node_id: String,
    pub parent_node_id: String,
    pub document_id: String,
    pub path: String,
    pub content: String,
    pub image_url: Option<String>,
    pub metadata: Value,
}

pub struct PostgresRepository {
    pool: PgPool,
    summary_table: String,
    page_table: String,
}

impl PostgresRepository {
    #[allow(clippy::too_many_arguments)]
    pub async fn new(
        dsn: &str,
        summary_table: &str,
        page_table: &str,
        pool_min: u32,
        pool_max: u32,
        connect_timeout_ms: u64,
        statement_timeout_ms: u64,
    ) -> CoreResult<Self> {
        if dsn.trim().is_empty() {
            return Err(CoreError::InvalidConfig(
                "postgres.dsn은 비어 있을 수 없습니다".to_string(),
            ));
        }

        validate_identifier(summary_table, "postgres.summary_table")?;
        validate_identifier(page_table, "postgres.page_table")?;

        let pool = PgPoolOptions::new()
            .min_connections(pool_min)
            .max_connections(pool_max.max(pool_min))
            .acquire_timeout(std::time::Duration::from_millis(connect_timeout_ms.max(1)))
            .connect(dsn)
            .await
            .map_err(|error| CoreError::Db(format!("Postgres 연결 실패: {}", error)))?;

        let timeout_statement = format!("SET statement_timeout = {}", statement_timeout_ms.max(1));
        sqlx::query(&timeout_statement)
            .execute(&pool)
            .await
            .map_err(|error| CoreError::Db(format!("statement_timeout 설정 실패: {}", error)))?;

        Ok(Self {
            pool,
            summary_table: summary_table.to_string(),
            page_table: page_table.to_string(),
        })
    }

    pub async fn search_summary_nodes(
        &self,
        query_embedding: &[f32],
        limit: usize,
    ) -> CoreResult<Vec<SummaryNodeRecord>> {
        let vector_literal = to_pgvector_literal(query_embedding)?;
        let sql = format!(
            "SELECT node_id, path::text AS path, (1 - (embedding <=> $1::vector)) AS score \
             FROM {} ORDER BY embedding <=> $1::vector LIMIT $2",
            self.summary_table
        );

        let rows = sqlx::query(&sql)
            .bind(vector_literal)
            .bind(limit as i64)
            .fetch_all(&self.pool)
            .await
            .map_err(|error| CoreError::Db(format!("summary 조회 실패: {}", error)))?;

        rows.into_iter()
            .map(map_summary_row)
            .collect::<CoreResult<Vec<_>>>()
    }

    pub async fn fetch_pages_under_path(
        &self,
        path: &str,
        limit: usize,
    ) -> CoreResult<Vec<PageNodeRecord>> {
        let sql = format!(
            "SELECT node_id, parent_node_id, path::text AS path, content, image_url \
             FROM {} WHERE path <@ $1::ltree ORDER BY path LIMIT $2",
            self.page_table
        );

        let rows = sqlx::query(&sql)
            .bind(path)
            .bind(limit as i64)
            .fetch_all(&self.pool)
            .await
            .map_err(|error| CoreError::Db(format!("page 조회 실패: {}", error)))?;

        rows.into_iter()
            .map(map_page_row)
            .collect::<CoreResult<Vec<_>>>()
    }

    pub async fn upsert_summary_nodes(&self, rows: &[IngestionSummaryNodeRecord]) -> CoreResult<u64> {
        if rows.is_empty() {
            return Ok(0);
        }

        let sql = format!(
            "INSERT INTO {} \
             (node_id, document_id, path, summary_text, embedding, metadata, updated_at) \
             VALUES ($1, $2, $3::ltree, $4, $5::vector, $6, NOW()) \
             ON CONFLICT (node_id) DO UPDATE SET \
             document_id = EXCLUDED.document_id, \
             path = EXCLUDED.path, \
             summary_text = EXCLUDED.summary_text, \
             embedding = EXCLUDED.embedding, \
             metadata = EXCLUDED.metadata, \
             updated_at = NOW()",
            self.summary_table
        );

        let mut affected = 0u64;
        for row in rows {
            let vector_literal = to_pgvector_literal(&row.embedding)?;
            let result = sqlx::query(&sql)
                .bind(&row.node_id)
                .bind(&row.document_id)
                .bind(&row.path)
                .bind(&row.summary_text)
                .bind(vector_literal)
                .bind(&row.metadata)
                .execute(&self.pool)
                .await
                .map_err(|error| CoreError::Db(format!("summary upsert 실패: {}", error)))?;
            affected = affected.saturating_add(result.rows_affected());
        }

        Ok(affected)
    }

    pub async fn upsert_page_nodes(&self, rows: &[IngestionPageNodeRecord]) -> CoreResult<u64> {
        if rows.is_empty() {
            return Ok(0);
        }

        let sql = format!(
            "INSERT INTO {} \
             (node_id, parent_node_id, document_id, path, content, image_url, metadata, updated_at) \
             VALUES ($1, $2, $3, $4::ltree, $5, $6, $7, NOW()) \
             ON CONFLICT (node_id) DO UPDATE SET \
             parent_node_id = EXCLUDED.parent_node_id, \
             document_id = EXCLUDED.document_id, \
             path = EXCLUDED.path, \
             content = EXCLUDED.content, \
             image_url = EXCLUDED.image_url, \
             metadata = EXCLUDED.metadata, \
             updated_at = NOW()",
            self.page_table
        );

        let mut affected = 0u64;
        for row in rows {
            let result = sqlx::query(&sql)
                .bind(&row.node_id)
                .bind(&row.parent_node_id)
                .bind(&row.document_id)
                .bind(&row.path)
                .bind(&row.content)
                .bind(&row.image_url)
                .bind(&row.metadata)
                .execute(&self.pool)
                .await
                .map_err(|error| CoreError::Db(format!("page upsert 실패: {}", error)))?;
            affected = affected.saturating_add(result.rows_affected());
        }

        Ok(affected)
    }

    pub async fn touch_summary_nodes(&self, document_id: &str) -> CoreResult<u64> {
        let sql = format!(
            "UPDATE {} SET updated_at = NOW() WHERE document_id = $1",
            self.summary_table
        );

        let result = sqlx::query(&sql)
            .bind(document_id)
            .execute(&self.pool)
            .await
            .map_err(|error| CoreError::Db(format!("summary 갱신 실패: {}", error)))?;

        Ok(result.rows_affected())
    }
}

fn map_summary_row(row: PgRow) -> CoreResult<SummaryNodeRecord> {
    let node_id = row
        .try_get::<String, _>("node_id")
        .map_err(|error| CoreError::Db(format!("summary.node_id 파싱 실패: {}", error)))?;
    let path = row
        .try_get::<String, _>("path")
        .map_err(|error| CoreError::Db(format!("summary.path 파싱 실패: {}", error)))?;
    let score = row
        .try_get::<f32, _>("score")
        .map_err(|error| CoreError::Db(format!("summary.score 파싱 실패: {}", error)))?;

    Ok(SummaryNodeRecord {
        node_id,
        path,
        score: score.clamp(0.0, 1.0),
    })
}

fn map_page_row(row: PgRow) -> CoreResult<PageNodeRecord> {
    let node_id = row
        .try_get::<String, _>("node_id")
        .map_err(|error| CoreError::Db(format!("page.node_id 파싱 실패: {}", error)))?;
    let parent_node_id = row
        .try_get::<String, _>("parent_node_id")
        .map_err(|error| CoreError::Db(format!("page.parent_node_id 파싱 실패: {}", error)))?;
    let path = row
        .try_get::<String, _>("path")
        .map_err(|error| CoreError::Db(format!("page.path 파싱 실패: {}", error)))?;
    let content = row
        .try_get::<String, _>("content")
        .map_err(|error| CoreError::Db(format!("page.content 파싱 실패: {}", error)))?;
    let image_url = row
        .try_get::<Option<String>, _>("image_url")
        .map_err(|error| CoreError::Db(format!("page.image_url 파싱 실패: {}", error)))?;

    Ok(PageNodeRecord {
        node_id,
        parent_node_id,
        path,
        content,
        image_url,
    })
}
