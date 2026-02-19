use numpy::PyReadonlyArray1;
use pyo3::prelude::*;
use std::sync::Arc;

#[derive(Debug, Default)]
pub struct EngineState {
    pub index_root: String,
}

#[pyclass(name = "SearchEngine")]
pub struct PySearchEngine {
    state: Arc<EngineState>,
}

#[pymethods]
impl PySearchEngine {
    #[new]
    pub fn new(index_root: String) -> Self {
        Self {
            state: Arc::new(EngineState { index_root }),
        }
    }

    #[getter]
    pub fn index_root(&self) -> String {
        self.state.index_root.clone()
    }

    pub fn search(&self, _query: PyReadonlyArray1<'_, f32>, _top_k: usize) -> PyResult<(Vec<u32>, Vec<f32>)> {
        // Placeholder: return Struct-of-Arrays shape (ids, scores).
        Ok((Vec::new(), Vec::new()))
    }
}
