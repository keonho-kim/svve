pub fn dot(left: &[f32], right: &[f32]) -> f32 {
    left.iter()
        .zip(right.iter())
        .map(|(l, r)| l * r)
        .sum::<f32>()
}

pub fn l2_norm(values: &[f32]) -> f32 {
    values.iter().map(|v| v * v).sum::<f32>().sqrt()
}

pub fn normalize_in_place(values: &mut [f32]) -> Option<()> {
    let norm = l2_norm(values);
    if norm <= f32::EPSILON {
        return None;
    }

    for value in values.iter_mut() {
        *value /= norm;
    }
    Some(())
}
