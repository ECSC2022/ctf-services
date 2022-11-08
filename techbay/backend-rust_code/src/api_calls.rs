use crate::{
    api_models::{LoginCredentials, NewUser, UserInfo, CurrentUserInfo},
    auth::{create_jwt, Role},
    data_access::DBAccessManager,
    errors::{AppError, ErrorType},
    models::users::CreateUserDTO,
    parser::render,
};
use serde::Serialize;
use sha256::digest;
use tracing::{error, info};

use std::fs;

pub async fn register(
    db_manager: DBAccessManager,
    new_user: NewUser,
) -> Result<impl warp::Reply, warp::Rejection> {
    info!("Handeling register new user.");

    let picture_bytes = base64::decode(new_user.clone().passport.clone()).map_err(|err| {
        AppError::new(
            format!("Error parsing base64 encoded passport. {}", err.to_string()).as_str(),
            ErrorType::ValidationError,
        )
    })?;
    let mime_type = tree_magic::from_u8(&picture_bytes);

    info!("{}", mime_type.clone());

    let passport_name = digest(new_user.clone().username.clone());

    render(picture_bytes, passport_name, mime_type)?;

    let create_user_dto = CreateUserDTO::from_new_user(new_user.clone());
    let _user_entry = db_manager.create_user(create_user_dto)?;

    Ok(warp::reply::reply())
}

pub async fn login(
    db_manager: DBAccessManager,
    login: LoginCredentials,
) -> Result<impl warp::Reply, warp::Rejection> {
    info!("Handeling login.");

    let user_dto = db_manager.login(login.username, login.hashed_password)?;
    let token = create_jwt(user_dto.id.unwrap(), &Role::User, user_dto.clone().username.clone(), user_dto.clone().displayname.clone())?;
    let response = UserInfo::from_user_dto(user_dto, &token);
 
    respond(response, warp::http::StatusCode::OK)
}

pub async fn current_user(
    db_manager: DBAccessManager,
    uid: i32
) -> Result<impl warp::Reply, warp::Rejection> {
    info!("Handeling current-user.");

    let user_dto = db_manager.get_user(uid)?;

    let response = CurrentUserInfo::from_user_dto(user_dto, ""); // How to handle the token hear. :>

    respond(response, warp::http::StatusCode::OK)
}

pub async fn passport(
    db_manager: DBAccessManager,
    uid: i32
) -> Result<impl warp::Reply, warp::Rejection> {
    info!("Handeling passport.");

    let user_dto = db_manager.get_user(uid)?;

    let passport_name = digest(user_dto.username.clone());

    let passport_bytes = fs::read(&format!("data/{}.png", passport_name)).map_err(|err| {
        AppError::new(
            format!("Error reading passport. {}", err.to_string()).as_str(),
            ErrorType::ValidationError,
        )
    })?;

    let mime_type = tree_magic::from_u8(&passport_bytes);

    if mime_type != "image/png" {
        return respond(Ok(format!("Wrong passport file format!")), warp::http::StatusCode::NOT_ACCEPTABLE);
    }

    let base64_string = base64::encode(&passport_bytes);

    respond(Ok(base64_string), warp::http::StatusCode::OK)
}

fn respond<T: Serialize>(
    result: Result<T, AppError>,
    status: warp::http::StatusCode,
) -> Result<impl warp::Reply, warp::Rejection> {
    match result {
        Ok(response) => Ok(warp::reply::with_status(
            warp::reply::json(&response),
            status,
        )),
        Err(err) => {
            error!("Error while trying to repond: {}", err.to_string());
            Err(warp::reject::custom(err))
        }
    }
}
