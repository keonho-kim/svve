// 목적:
// - Rust 코어 계층의 표준 오류 타입을 정의한다.
//
// 설명:
// - 입력/설정/DB/HTTP/직렬화 오류를 명시적으로 구분해 Python에 전달한다.
//
// 디자인 패턴:
// - 도메인 오류 열거형(Domain Error Enum).
//
// 참조:
// - src_rs/core/search_pipeline.rs
// - src_rs/core/ingestion_pipeline.rs

use thiserror::Error;

/// 코어 계층에서 공통으로 사용하는 오류 열거형이다.
#[derive(Debug, Error)]
pub enum CoreError {
    #[error("입력값이 유효하지 않습니다: {0}")]
    InvalidInput(String),
    #[error("설정값이 유효하지 않습니다: {0}")]
    InvalidConfig(String),
    #[error("데이터베이스 작업에 실패했습니다: {0}")]
    Db(String),
    #[error("필터 HTTP 호출에 실패했습니다: {0}")]
    Http(String),
    #[error("직렬화/역직렬화에 실패했습니다: {0}")]
    Serialization(String),
    #[error("런타임 처리 중 오류가 발생했습니다: {0}")]
    Runtime(String),
}

pub type CoreResult<T> = Result<T, CoreError>;
