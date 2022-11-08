#[macro_use]
extern crate diesel;

mod api_calls;
mod api_models;
mod auth;
mod data_access;
mod errors;
mod models;
mod parser;
mod routes;
mod schema;

use std::{env, sync::Once, path::Path, fs};

use color_eyre::Report;
use diesel::{
    r2d2::{ConnectionManager, Pool},
    PgConnection,
};
use dotenv::dotenv;
use rand::distributions::{Alphanumeric, DistString};
use tracing::{info, error};
use tracing_subscriber::EnvFilter;
use warp::Filter;

use crate::routes::api_filters;

static INIT: Once = Once::new();

type DBPool = Pool<ConnectionManager<PgConnection>>;

#[tokio::main]
async fn main() -> Result<(), Report> {
    initial_setup()?;
    let mut private_key: String = "53cr3t_k3y".to_string();//Alphanumeric.sample_string(&mut rand::thread_rng(), 32);
    if Path::new("private.key").exists() {
        private_key = fs::read_to_string("private.key").unwrap();
    }
    info!("Loading JWT Token: {}", private_key.clone());
    env::set_var("JWT_SECRET", &private_key);
    match dotenv() {
        Ok(_) => info!("Dotenv loaded!"),
        Err(_) => error!("Dotenv file not loaded!")
    }

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL env not set");

    let db_pool = initialize_db_pool(database_url.as_str())?;

    let routes = api_filters(db_pool).recover(errors::handle_rejection);

    info!("Starting authentication service on port 3030...");

    // Start up the server...
    warp::serve(routes).run(([0, 0, 0, 0], 3030)).await;

    Ok(())
}

fn initial_setup() -> Result<(), Report> {
    let mut result: Result<(), Report> = Ok(());
    INIT.call_once(|| {
        if std::env::var("RUST_LIB_BACKTRACE").is_err() {
            std::env::set_var("RUST_LIB_BACKTRACE", "1")
        }
        if std::env::var("RUST_LOG").is_err() {
            #[cfg(not(debug_assertions))]
            std::env::set_var("RUST_LOG", "info");
            #[cfg(debug_assertions)]
            std::env::set_var("RUST_LOG", "debug");
        }
        result = color_eyre::install().and_then(|_| {
            Ok(tracing_subscriber::fmt::fmt()
                .with_env_filter(EnvFilter::from_default_env())
                .init())
        });
    });
    result
}

fn initialize_db_pool(db_url: &str) -> Result<DBPool, Report> {
    let manager = ConnectionManager::<PgConnection>::new(db_url);
    Ok(Pool::new(manager)?)
}
