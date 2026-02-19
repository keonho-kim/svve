#![allow(non_local_definitions)]

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

pub mod math {
    pub mod linalg;
    pub mod normalize;
    pub mod topk;
}

pub mod vdb {
    pub mod adapter;
    pub mod fetch;
    pub mod query;
}

use api::search_engine::PySearchEngine;

#[pymodule]
fn _svve_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySearchEngine>()?;
    Ok(())
}
