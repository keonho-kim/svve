// 목적:
// - 페이지 후보에 대한 외부 필터 HTTP 호출을 담당한다.
//
// 설명:
// - 질문/페이지 본문을 HTTP 엔드포인트에 전달하고 keep 여부를 판정한다.
// - 병렬 처리 수는 semaphore로 제한한다.
//
// 디자인 패턴:
// - 어댑터(Adapter) + 제한 병렬 처리(Bounded Concurrency).
//
// 참조:
// - src_rs/core/search_pipeline.rs

use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::sync::Arc;
use tokio::sync::{OwnedSemaphorePermit, Semaphore};
use tokio::task::JoinSet;

use crate::core::errors::{CoreError, CoreResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterHttpConfigPayload {
    pub url: String,
    pub timeout_ms: u64,
    pub auth_token: Option<String>,
    pub model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterDecision {
    pub node_id: String,
    pub keep: bool,
    pub reason: String,
}

#[derive(Debug, Clone)]
pub struct FilterCandidateInput {
    pub node_id: String,
    pub content: String,
}

#[derive(Clone)]
pub struct FilterHttpClient {
    client: Client,
    config: FilterHttpConfigPayload,
}

impl FilterHttpClient {
    pub fn new(config: FilterHttpConfigPayload) -> CoreResult<Self> {
        if config.url.trim().is_empty() {
            return Err(CoreError::InvalidConfig(
                "filter_http.url은 비어 있을 수 없습니다".to_string(),
            ));
        }

        if config.timeout_ms == 0 {
            return Err(CoreError::InvalidConfig(
                "filter_http.timeout_ms는 1 이상이어야 합니다".to_string(),
            ));
        }

        let client = Client::builder()
            .timeout(std::time::Duration::from_millis(config.timeout_ms))
            .build()
            .map_err(|error| CoreError::Http(format!("HTTP 클라이언트 생성 실패: {}", error)))?;

        Ok(Self { client, config })
    }

    pub async fn filter_candidates(
        &self,
        question: &str,
        candidates: &[FilterCandidateInput],
        concurrency: usize,
    ) -> CoreResult<Vec<FilterDecision>> {
        if question.trim().is_empty() {
            return Err(CoreError::InvalidInput(
                "question은 비어 있을 수 없습니다".to_string(),
            ));
        }

        let bounded = concurrency.max(1);
        let semaphore = Arc::new(Semaphore::new(bounded));
        let mut join_set = JoinSet::new();

        for candidate in candidates {
            let permit = semaphore.clone().acquire_owned().await.map_err(|error| {
                CoreError::Runtime(format!("필터 semaphore 획득 실패: {}", error))
            })?;
            let cloned_client = self.clone();
            let cloned_question = question.to_string();
            let cloned_candidate = candidate.clone();

            join_set.spawn(async move {
                let _permit: OwnedSemaphorePermit = permit;
                cloned_client
                    .filter_single(&cloned_question, &cloned_candidate)
                    .await
            });
        }

        let mut decisions = Vec::with_capacity(candidates.len());
        while let Some(joined) = join_set.join_next().await {
            let decision = joined.map_err(|error| {
                CoreError::Runtime(format!("필터 작업 조인 실패: {}", error))
            })??;
            decisions.push(decision);
        }

        decisions.sort_by(|left, right| left.node_id.cmp(&right.node_id));
        Ok(decisions)
    }

    async fn filter_single(
        &self,
        question: &str,
        candidate: &FilterCandidateInput,
    ) -> CoreResult<FilterDecision> {
        #[derive(Serialize)]
        struct FilterRequest<'a> {
            question: &'a str,
            content: &'a str,
            model: Option<&'a str>,
        }

        let model_ref = self.config.model.as_deref();
        let request_body = FilterRequest {
            question,
            content: &candidate.content,
            model: model_ref,
        };

        let mut request_builder = self.client.post(self.config.url.as_str()).json(&request_body);
        if let Some(token) = self.config.auth_token.as_ref() {
            request_builder = request_builder.bearer_auth(token);
        }

        let response = request_builder
            .send()
            .await
            .map_err(|error| CoreError::Http(format!("필터 HTTP 요청 실패: {}", error)))?;

        let status = response.status();
        let body = response
            .text()
            .await
            .map_err(|error| CoreError::Http(format!("필터 HTTP 본문 읽기 실패: {}", error)))?;

        if !status.is_success() {
            return Err(CoreError::Http(format!(
                "필터 HTTP 상태 오류: status={}, body={}",
                status, body
            )));
        }

        let (keep, reason) = parse_filter_response(&body).map_err(|error| {
            CoreError::Serialization(format!(
                "필터 응답 파싱 실패: {}, body={}",
                error, body
            ))
        })?;

        Ok(FilterDecision {
            node_id: candidate.node_id.clone(),
            keep,
            reason,
        })
    }
}

fn parse_filter_response(body: &str) -> Result<(bool, String), String> {
    let trimmed = body.trim();

    if trimmed == "1" {
        return Ok((true, "binary-response".to_string()));
    }
    if trimmed == "0" {
        return Ok((false, "binary-response".to_string()));
    }

    let value: Value = serde_json::from_str(trimmed)
        .map_err(|error| format!("JSON 파싱 실패: {}", error))?;

    if let Some(keep) = value.get("keep").and_then(Value::as_bool) {
        let reason = value
            .get("reason")
            .and_then(Value::as_str)
            .unwrap_or("json-response")
            .to_string();
        return Ok((keep, reason));
    }

    if let Some(flag) = value.get("result").and_then(Value::as_str) {
        if flag == "1" {
            return Ok((true, "json-result".to_string()));
        }
        if flag == "0" {
            return Ok((false, "json-result".to_string()));
        }
    }

    Err("지원하지 않는 필터 응답 형식".to_string())
}
