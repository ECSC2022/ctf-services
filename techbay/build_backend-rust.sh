#!/bin/bash

cd backend-rust_code
cargo build --release
cd ..
cp backend-rust_code/target/release/backend-rust dist/backend-rust/backend-rust
