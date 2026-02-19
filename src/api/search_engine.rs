use numpy::PyReadonlyArray1;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyAny;

use crate::core::pipeline;
use crate::vdb::adapter::CallbackVdb;

#[pyclass(name = "SearchEngine")]
pub struct PySearchEngine;

#[pymethods]
impl PySearchEngine {
    #[new]
    pub fn new() -> Self {
        Self
    }

    pub fn search(
        &self,
        query: PyReadonlyArray1<'_, f32>,
        top_k: usize,
        search_fn: Py<PyAny>,
    ) -> PyResult<(Vec<u32>, Vec<f32>)> {
        let query_slice = query
            .as_slice()
            .map_err(|_| PyValueError::new_err("query는 contiguous float32 1D 배열이어야 합니다"))?;

        let callback_adapter = CallbackVdb::new(search_fn, query_slice.len());
        pipeline::execute_search(&callback_adapter, query_slice, top_k)
            .map_err(PyRuntimeError::new_err)
    }
}
