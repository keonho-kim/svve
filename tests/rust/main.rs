use std::collections::HashMap;

use _svve_core::core::pipeline;
use _svve_core::core::voting;
use _svve_core::math::linalg;
use _svve_core::vdb::adapter::{DocVector, ScoredDoc, VdbAdapter};
use _svve_core::vdb::query;

struct InMemoryVdb {
    dim: usize,
    docs: Vec<DocVector>,
    by_id: HashMap<u32, Vec<f32>>,
}

impl InMemoryVdb {
    fn from_docs(raw_docs: Vec<(u32, Vec<f32>)>) -> Self {
        let dim = raw_docs
            .first()
            .map(|(_, vector)| vector.len())
            .expect("테스트 문서가 비어 있으면 안 됩니다");

        let mut docs = Vec::with_capacity(raw_docs.len());
        let mut by_id = HashMap::with_capacity(raw_docs.len());

        for (id, mut vector) in raw_docs {
            assert_eq!(
                vector.len(),
                dim,
                "모든 테스트 문서는 동일한 차원을 가져야 합니다"
            );
            linalg::normalize_in_place(&mut vector).expect("0-벡터는 테스트 데이터로 허용되지 않습니다");
            by_id.insert(id, vector.clone());
            docs.push(DocVector { id, vector });
        }

        Self { dim, docs, by_id }
    }
}

impl VdbAdapter for InMemoryVdb {
    fn dim(&self) -> usize {
        self.dim
    }

    fn search(&self, query: &[f32], limit: usize) -> Result<Vec<ScoredDoc>, String> {
        if query.len() != self.dim {
            return Err(format!(
                "쿼리 차원이 일치하지 않습니다: expected={}, actual={}",
                self.dim,
                query.len()
            ));
        }

        let mut hits = self
            .docs
            .iter()
            .map(|doc| (doc.id, linalg::dot(query, &doc.vector)))
            .collect::<Vec<_>>();

        hits.sort_by(|left, right| {
            right
                .1
                .partial_cmp(&left.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| left.0.cmp(&right.0))
        });
        hits.truncate(limit.min(hits.len()));

        Ok(hits)
    }

    fn fetch_vectors(&self, doc_ids: &[u32]) -> Result<Vec<DocVector>, String> {
        let mut vectors = Vec::with_capacity(doc_ids.len());
        for doc_id in doc_ids {
            let vector = self.by_id.get(doc_id).ok_or_else(|| {
                format!("doc_id={} 벡터를 테스트 어댑터에서 찾을 수 없습니다", doc_id)
            })?;
            vectors.push(DocVector {
                id: *doc_id,
                vector: vector.clone(),
            });
        }
        Ok(vectors)
    }
}

fn fixture_adapter() -> InMemoryVdb {
    InMemoryVdb::from_docs(vec![
        (1, vec![1.0, 0.0, 0.0, 0.0]),
        (2, vec![0.9, 0.1, 0.0, 0.0]),
        (3, vec![0.0, 1.0, 0.0, 0.0]),
        (4, vec![0.0, 0.0, 1.0, 0.0]),
        (5, vec![0.0, 0.0, 0.0, 1.0]),
        (6, vec![0.7, 0.2, 0.1, 0.0]),
    ])
}

#[test]
fn query_segmentation_is_fixed_to_four_ranges() {
    let ranges = query::segment_ranges(10);
    assert_eq!(ranges.len(), query::SEGMENT_COUNT);
    assert_eq!(ranges[0].start, 0);
    assert_eq!(ranges.last().expect("세그먼트 범위가 필요합니다").end, 10);
}

#[test]
fn voting_rule_keeps_strong_or_weak_candidates_only() {
    let segments = vec![
        vec![(10, 0.9), (20, 0.8)],
        vec![(10, 0.95), (30, 0.7)],
        vec![(10, 0.88)],
        vec![(40, 0.99)],
    ];

    let merged = voting::merge_segment_results(&segments);
    let survivors = voting::select_survivor_ids(&merged, 5);

    assert_eq!(survivors, vec![10]);
}

#[test]
fn fixed_pipeline_returns_requested_top_k_when_available() {
    let adapter = fixture_adapter();

    let query = vec![1.0, 0.0, 0.0, 0.0];
    let (ids, scores) =
        pipeline::execute_search(&adapter, &query, 3).expect("검색이 성공해야 합니다");

    assert_eq!(ids.len(), 3);
    assert_eq!(scores.len(), 3);
    assert_eq!(ids[0], 1);
}
