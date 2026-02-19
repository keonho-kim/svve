use crate::vdb::adapter::{DocId, DocVector, VdbAdapter};

pub fn fetch_vectors(
    adapter: &dyn VdbAdapter,
    doc_ids: &[DocId],
) -> Result<Vec<DocVector>, String> {
    adapter.fetch_vectors(doc_ids)
}

pub fn centroid(vectors: &[DocVector], dim: usize) -> Result<Vec<f32>, String> {
    if vectors.is_empty() {
        return Err("중심 벡터를 계산할 생존 문서가 없습니다".to_string());
    }

    let mut center = vec![0.0; dim];
    for doc in vectors {
        if doc.vector.len() != dim {
            return Err(format!(
                "생존 벡터 차원이 일치하지 않습니다: expected={}, actual={}, doc_id={}",
                dim,
                doc.vector.len(),
                doc.id
            ));
        }

        for (dst, src) in center.iter_mut().zip(doc.vector.iter()) {
            *dst += *src;
        }
    }

    let inv = 1.0f32 / vectors.len() as f32;
    for value in center.iter_mut() {
        *value *= inv;
    }
    Ok(center)
}
