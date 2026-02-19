use pyo3::prelude::*;
use pyo3::types::PyModule;

pub mod api {
    pub mod search_engine;
}

pub mod core {
    pub mod expansion;
    pub mod pipeline;
    pub mod voting;
}

pub mod index {
    pub mod mmap_loader;
    pub mod tier1_bq;
    pub mod tier2_float;
}

pub mod math {
    pub mod linalg;
    pub mod simd_hamming;
    pub mod whitening;
}

use api::search_engine::PySearchEngine;

#[pymodule]
fn _svve_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySearchEngine>()?;
    Ok(())
}
