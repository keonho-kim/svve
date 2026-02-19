use rstest::rstest;

#[rstest]
#[case(1, 2, 3)]
#[case(10, 5, 15)]
fn smoke_addition(#[case] left: i32, #[case] right: i32, #[case] expected: i32) {
    assert_eq!(left + right, expected);
}
