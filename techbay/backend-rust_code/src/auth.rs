use crate::errors::{AppError, ErrorType};
use chrono::prelude::*;
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use lazy_static::lazy_static;
use serde::{Deserialize, Serialize};
use std::fmt;
use tracing::error;
use warp::{
    filters::header::headers_cloned,
    http::header::{HeaderMap, HeaderValue, AUTHORIZATION},
    reject, Filter, Rejection,
};

const BEARER: &str = "Bearer ";
lazy_static! {
    static ref JWT_SECRET: Vec<u8> = std::env::var("JWT_SECRET").unwrap().as_bytes().to_vec();
}


#[derive(Debug, Deserialize, Serialize, Clone, PartialEq)]
pub enum Role {
    User,
    Admin,
}
impl Role {
    #[allow(dead_code)]
    pub fn from_str(role: &str) -> Role {
        match role {
            "Admin" => Role::Admin,
            &_ => Role::Admin
        }
    }
}

impl fmt::Display for Role {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Role::User => write!(f, "User"),
            Role::Admin => write!(f, "Admin"),
        }
    }
}

#[derive(Debug, Deserialize, Serialize)]
struct Claims {
    user: User,
    exp: usize,
}

#[derive(Debug, Deserialize, Serialize)]
struct User {
    #[serde(rename = "userId")]
    user_id: i32,
    username: String,
    displayname: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    role: Option<Role>,
}

pub fn with_auth(is_admin: bool) -> impl Filter<Extract = (i32,), Error = Rejection> + Clone {
    headers_cloned()
        .map(move |headers: HeaderMap<HeaderValue>| (is_admin, headers))
        .and_then(authorize)
}

#[allow(unused_variables)]
pub fn create_jwt(uid: i32, role: &Role, username: String, displayname: String) -> Result<String, AppError> {
    let expiration = Utc::now()
        .checked_add_signed(chrono::Duration::minutes(60))
        .expect("valid timestamp")
        .timestamp();

    let claims = Claims {
        user: User {
            user_id: uid,
            username,
            displayname,
            role: Some(Role::User)
        },
        exp: expiration as usize,
    };
    let header = Header::new(Algorithm::HS512);
    encode(&header, &claims, &EncodingKey::from_secret(&JWT_SECRET))
        .map_err(|_| AppError::new("JWT creation error.", ErrorType::Internal))
}

async fn authorize(
    (is_admin, headers): (bool, HeaderMap<HeaderValue>),
) -> Result<i32, warp::Rejection> {
    match jwt_from_header(&headers) {
        Ok(jwt) => {
            let decoded = decode::<Claims>(
                &jwt,
                &DecodingKey::from_secret(&JWT_SECRET),
                &Validation::new(Algorithm::HS512),
            )
            .map_err(|err| {
                error!("{:?}", err);
                reject::custom(AppError::new(
                    "JWT Parsing error.",
                    ErrorType::ValidationError,
                ))
            })?;

            match is_admin {
                false => Ok(decoded.claims.user.user_id),
                true if decoded.claims.user.role == Some(Role::Admin) => Ok(decoded.claims.user.user_id),
                _ => Err(reject::custom(AppError::new("Not authorized!", ErrorType::Unauthorized)))
            }
        }
        Err(e) => {
            return Err(reject::custom(AppError::new(
                &format!("JWT from header error: {}", e.to_string()),
                e.err_type,
            )))
        }
    }
}

fn jwt_from_header(headers: &HeaderMap<HeaderValue>) -> Result<String, AppError> {
    let header = match headers.get(AUTHORIZATION) {
        Some(v) => v,
        None => {
            return Err(AppError::new(
                "No Authorization in header.",
                ErrorType::Unauthenticated,
            ))
        }
    };
    let auth_header = match std::str::from_utf8(header.as_bytes()) {
        Ok(v) => v,
        Err(_) => {
            return Err(AppError::new(
                "No Authorization in header.",
                ErrorType::Unauthenticated,
            ))
        }
    };
    if !auth_header.starts_with(BEARER) {
        return Err(AppError::new(
            "Invalid Authorization in header.",
            ErrorType::Unauthenticated,
        ));
    }
    Ok(auth_header.trim_start_matches(BEARER).to_owned())
}
