#![allow(non_local_definitions)]

// 목적:
// - Vtree Search Rust 확장 모듈의 진입점을 제공한다.
//
// 설명:
// - 1차 전환 단계에서는 Python 바인딩과 모듈 경계만 확정한다.
// - 실제 검색/필터링 런타임은 2차 구현에서 채운다.
//
// 디자인 패턴:
// - 계층형 모듈 구조(api/core/index/math).
//
// 참조:
// - src_rs/api/search_bridge.rs
// - docs/rust/module_reference.md

use pyo3::prelude::*;
use pyo3::types::PyModule;

pub mod api;
pub mod core;
pub mod index;
pub mod math;

use api::ingestion_bridge::PyIngestionBridge;
use api::search_bridge::PySearchBridge;

#[pymodule]
fn _vtree_search(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySearchBridge>()?;
    m.add_class::<PyIngestionBridge>()?;
    Ok(())
}
