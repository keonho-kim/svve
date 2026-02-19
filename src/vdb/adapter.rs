use std::collections::HashMap;
use std::sync::Mutex;

use numpy::PyArray1;
use pyo3::prelude::*;
use pyo3::types::PyAny;

use crate::math::{linalg, topk};

pub type DocId = u32;
pub type ScoredDoc = (DocId, f32);

#[derive(Debug, Clone)]
pub struct DocVector {
    pub id: DocId,
    pub vector: Vec<f32>,
}

pub trait VdbAdapter: Send + Sync {
    fn dim(&self) -> usize;
    fn search(&self, query: &[f32], limit: usize) -> Result<Vec<ScoredDoc>, String>;
    fn fetch_vectors(&self, doc_ids: &[DocId]) -> Result<Vec<DocVector>, String>;
}

#[derive(Debug)]
pub struct CallbackVdb {
    dim: usize,
    search_fn: Py<PyAny>,
    vector_cache: Mutex<HashMap<DocId, Vec<f32>>>,
}

impl CallbackVdb {
    pub fn new(search_fn: Py<PyAny>, dim: usize) -> Self {
        Self {
            dim,
            search_fn,
            vector_cache: Mutex::new(HashMap::new()),
        }
    }
}

impl VdbAdapter for CallbackVdb {
    fn dim(&self) -> usize {
        self.dim
    }

    fn search(&self, query: &[f32], limit: usize) -> Result<Vec<ScoredDoc>, String> {
        if limit == 0 {
            return Ok(Vec::new());
        }

        if query.len() != self.dim {
            return Err(format!(
                "콜백 검색 쿼리 차원이 일치하지 않습니다: expected={}, actual={}",
                self.dim,
                query.len()
            ));
        }

        let attached = Python::try_attach(|py| {
            let py_query = PyArray1::<f32>::from_slice(py, query);
            let result = self
                .search_fn
                .call1(py, (py_query, limit))
                .map_err(|err| format!("search_fn 호출 실패: {}", err))?;

            let (ids, scores, vectors): (Vec<u32>, Vec<f32>, Vec<Vec<f32>>) =
                result.extract(py).map_err(|err| {
                    format!(
                        "search_fn 반환 형식이 올바르지 않습니다: expected=(ids, scores, vectors), error={}",
                        err
                    )
                })?;

            if ids.len() != scores.len() || ids.len() != vectors.len() {
                return Err(format!(
                    "search_fn 반환 길이가 일치하지 않습니다: ids={}, scores={}, vectors={}",
                    ids.len(),
                    scores.len(),
                    vectors.len()
                ));
            }

            let mut cache = self
                .vector_cache
                .lock()
                .map_err(|_| "벡터 캐시 잠금을 획득할 수 없습니다".to_string())?;

            let mut hits = Vec::with_capacity(ids.len());
            for ((doc_id, score), mut vector) in ids
                .into_iter()
                .zip(scores.into_iter())
                .zip(vectors.into_iter())
            {
                if vector.len() != self.dim {
                    return Err(format!(
                        "search_fn 벡터 차원이 일치하지 않습니다: expected={}, actual={}, doc_id={}",
                        self.dim,
                        vector.len(),
                        doc_id
                    ));
                }
                if linalg::normalize_in_place(&mut vector).is_none() {
                    return Err(format!(
                        "search_fn이 0-벡터를 반환했습니다: doc_id={}",
                        doc_id
                    ));
                }

                cache.insert(doc_id, vector);
                hits.push((doc_id, score));
            }

            topk::sort_desc_take(&mut hits, limit);
            Ok(hits)
        });

        attached.unwrap_or_else(|| Err("Python 인터프리터에 attach할 수 없습니다".to_string()))
    }

    fn fetch_vectors(&self, doc_ids: &[DocId]) -> Result<Vec<DocVector>, String> {
        let cache = self
            .vector_cache
            .lock()
            .map_err(|_| "벡터 캐시 잠금을 획득할 수 없습니다".to_string())?;

        let mut vectors = Vec::with_capacity(doc_ids.len());
        for doc_id in doc_ids {
            let vector = cache.get(doc_id).ok_or_else(|| {
                format!(
                    "doc_id={} 벡터를 캐시에서 찾을 수 없습니다. search_fn이 각 hit의 벡터를 반드시 반환해야 합니다",
                    doc_id
                )
            })?;
            vectors.push(DocVector {
                id: *doc_id,
                vector: vector.clone(),
            });
        }
        Ok(vectors)
    }
}
