// 목적:
// - Python에서 호출 가능한 검색 브릿지 클래스를 제공한다.
//
// 설명:
// - JSON 페이로드를 입력받아 Rust 검색 파이프라인을 실행하고,
//   결과를 JSON 문자열로 반환한다.
//
// 디자인 패턴:
// - 파사드(Facade) + 실패 빠르게(Fail Fast).
//
// 참조:
// - src_rs/core/search_pipeline.rs

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use tokio::runtime::{Builder, Runtime};

use crate::core::search_pipeline::{execute_search, SearchRequestPayload};

/// Python에 노출되는 검색 브릿지 클래스다.
#[pyclass(name = "SearchBridge")]
pub struct PySearchBridge {
    phase: String,
}

#[pymethods]
impl PySearchBridge {
    /// 검색 브릿지 객체를 생성한다.
    #[new]
    pub fn new() -> Self {
        Self {
            phase: "phase3-search-db-only".to_string(),
        }
    }

    /// 현재 검색 브릿지 단계 정보를 반환한다.
    pub fn status(&self) -> String {
        self.phase.clone()
    }

    /// 검색 작업 페이로드(JSON)를 실행하고 결과 JSON을 반환한다.
    pub fn execute(&self, payload_json: &str) -> PyResult<String> {
        let payload: SearchRequestPayload = serde_json::from_str(payload_json).map_err(|error| {
            PyRuntimeError::new_err(format!(
                "검색 페이로드 JSON 파싱에 실패했습니다: {}",
                error
            ))
        })?;

        let runtime = create_runtime().map_err(PyRuntimeError::new_err)?;
        let result = runtime
            .block_on(execute_search(payload))
            .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;

        serde_json::to_string(&result)
            .map_err(|error| PyRuntimeError::new_err(format!("검색 결과 직렬화 실패: {}", error)))
    }
}

fn create_runtime() -> Result<Runtime, String> {
    Builder::new_multi_thread()
        .enable_all()
        .build()
        .map_err(|error| format!("Tokio 런타임 생성 실패: {}", error))
}
