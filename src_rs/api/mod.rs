// 목적:
// - Python FFI 경계 모듈을 선언한다.
//
// 설명:
// - 검색/적재 브릿지를 분리해 Python 계층에서 두 클래스로 사용할 수 있게 한다.
//
// 디자인 패턴:
// - 모듈 분리(Module Separation).
//
// 참조:
// - src_rs/api/search_bridge.rs
// - src_rs/api/ingestion_bridge.rs

pub mod ingestion_bridge;
pub mod search_bridge;
