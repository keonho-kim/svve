use crate::math::linalg;

pub fn normalized_copy(values: &[f32]) -> Option<Vec<f32>> {
    let mut normalized = values.to_vec();
    linalg::normalize_in_place(&mut normalized)?;
    Some(normalized)
}
