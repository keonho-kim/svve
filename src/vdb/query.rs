#[derive(Clone, Copy, Debug)]
pub struct SegmentRange {
    pub start: usize,
    pub end: usize,
}

pub const SEGMENT_COUNT: usize = 4;
pub const SEGMENT_TOP_K: usize = 100;
pub const SURVIVOR_COUNT: usize = 5;
pub const PRF_ALPHA: f32 = 0.7;
pub const MAX_REFINEMENT_ROUNDS: usize = 8;

pub fn segment_ranges(dim: usize) -> Vec<SegmentRange> {
    let mut ranges = Vec::with_capacity(SEGMENT_COUNT);
    let base_len = dim / SEGMENT_COUNT;
    let remainder = dim % SEGMENT_COUNT;

    let mut start = 0usize;
    for idx in 0..SEGMENT_COUNT {
        let extra = usize::from(idx < remainder);
        let end = start + base_len + extra;
        ranges.push(SegmentRange { start, end });
        start = end;
    }

    ranges
}

pub fn build_segment_query(query: &[f32], segment: SegmentRange) -> Vec<f32> {
    let mut projected = vec![0.0; query.len()];
    if segment.start < segment.end {
        projected[segment.start..segment.end].copy_from_slice(&query[segment.start..segment.end]);
    }
    projected
}
