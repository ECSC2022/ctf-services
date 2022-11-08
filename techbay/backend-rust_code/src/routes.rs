use crate::{
    api_calls,
    api_models::{LoginCredentials, NewUser},
    auth::{with_auth},
    data_access::DBAccessManager,
    errors::{AppError, ErrorType},
};
use diesel::{
    r2d2::{ConnectionManager, Pool},
    PgConnection,
};
use serde::de::DeserializeOwned;
use warp::{reject, Filter};

type SqlitePool = Pool<ConnectionManager<PgConnection>>;

pub fn api_filters(
    pool: SqlitePool,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path!("api" / ..).and(
        login(pool.clone())
            .or(register(pool.clone()))
            .or(passport(pool.clone()))
            .or(current_user(pool.clone()))
            .with(warp::trace::request()),
    )
}

pub fn login(
    pool: SqlitePool,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path!("auth" / "login")
        .and(warp::post())
        .and(with_db_access_manager(pool))
        .and(with_json_body::<LoginCredentials>())
        .and_then(api_calls::login)
}

pub fn register(
    pool: SqlitePool,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path!("auth" / "register")
        .and(warp::post())
        .and(with_db_access_manager(pool))
        .and(with_json_body::<NewUser>())
        .and_then(api_calls::register)
}

pub fn current_user(
    pool: SqlitePool,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path!("auth" / "current-user")
        .and(warp::get())
        .and(with_db_access_manager(pool))
        .and(with_auth(false))
        .and_then(api_calls::current_user)
}

pub fn passport(
    pool: SqlitePool,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path!("auth" / "passport")
        .and(warp::get())
        .and(with_db_access_manager(pool))
        //.and(with_auth(Role::Admin))
        .and(with_auth(true))
        .and_then(api_calls::passport)
}

fn with_db_access_manager(
    pool: SqlitePool,
) -> impl Filter<Extract = (DBAccessManager,), Error = warp::Rejection> + Clone {
    warp::any()
        .map(move || pool.clone())
        .and_then(|pool: SqlitePool| async move {
            match pool.get() {
                Ok(conn) => Ok(DBAccessManager::new(conn)),
                Err(err) => Err(reject::custom(AppError::new(
                    format!("Error getting connection from pool: {}", err.to_string()).as_str(),
                    ErrorType::Internal,
                ))),
            }
        })
}

fn with_json_body<T: DeserializeOwned + Send>(
) -> impl Filter<Extract = (T,), Error = warp::Rejection> + Clone {
    // When accepting a body, we want a JSON body
    // (and to reject huge payloads)...
    warp::body::content_length_limit(1024 * 140).and(warp::body::json())
}
