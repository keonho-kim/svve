// 목적:
// - 핵심 런타임 계층 모듈을 선언한다.
//
// 설명:
// - 검색/적재 파이프라인과 공통 오류 모델을 분리해 유지보수성을 높인다.
//
// 디자인 패턴:
// - 명시적 오류 모델(Explicit Error Model).
//
// 참조:
// - src_rs/core/errors.rs
// - src_rs/core/search_pipeline.rs
// - src_rs/core/ingestion_pipeline.rs

pub mod errors;
pub mod ingestion_pipeline;
pub mod search_pipeline;
