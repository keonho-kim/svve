// 목적:
// - SQL 관련 공통 유틸리티를 제공한다.
//
// 설명:
// - 동적 테이블명 검증, pgvector 리터럴 변환 등 DB 안전성 경계를 담당한다.
//
// 디자인 패턴:
// - 가드 함수(Guard Function).
//
// 참조:
// - src_rs/index/postgres_repo.rs

use crate::core::errors::{CoreError, CoreResult};

/// 테이블 식별자의 허용 문자를 검증한다.
pub fn validate_identifier(value: &str, field_name: &str) -> CoreResult<()> {
    if value.trim().is_empty() {
        return Err(CoreError::InvalidConfig(format!(
            "{}는 비어 있을 수 없습니다",
            field_name
        )));
    }

    let valid = value
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '_');

    if !valid {
        return Err(CoreError::InvalidConfig(format!(
            "{}에는 영문/숫자/밑줄만 사용할 수 있습니다: {}",
            field_name, value
        )));
    }

    Ok(())
}

/// float 벡터를 pgvector 문자열 리터럴로 변환한다.
pub fn to_pgvector_literal(values: &[f32]) -> CoreResult<String> {
    if values.is_empty() {
        return Err(CoreError::InvalidInput(
            "벡터는 최소 1개 이상의 값을 가져야 합니다".to_string(),
        ));
    }

    let parts = values
        .iter()
        .map(|value| format!("{:.8}", value))
        .collect::<Vec<_>>();

    Ok(format!("[{}]", parts.join(",")))
}
