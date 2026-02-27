// 목적:
// - PostgreSQL 인덱스 계층 모듈을 선언한다.
//
// 설명:
// - SQL 유틸과 저장소 구현을 분리해 유지보수성을 확보한다.
//
// 디자인 패턴:
// - 저장소 패턴(Repository Pattern).
//
// 참조:
// - src_rs/index/sql.rs
// - src_rs/index/postgres_repo.rs

pub mod postgres_repo;
pub mod sql;
