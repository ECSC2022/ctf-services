use serde_derive::{Deserialize, Serialize};
use sha256::digest;
use std::fs;

use crate::{
    errors::{AppError, ErrorType},
    models::users::UserDTO,
};

#[derive(Debug, Deserialize, Clone)]
pub struct LoginCredentials {
    pub username: String,
    #[serde(rename = "hashedPassword")]
    pub hashed_password: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct NewUser {
    pub username: String,
    #[serde(rename = "hashedPassword")]
    pub hashed_password: String,
    pub passport: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct UserInfo {
    #[serde(rename = "userId")]
    pub user_id: i32,
    pub username: String,
    pub displayname: String,
    pub token: String,
    pub passport: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CurrentUserInfo {
    #[serde(rename = "userId")]
    pub user_id: i32,
    pub username: String,
    pub displayname: String,
    pub token: String
}

impl UserInfo {
    pub fn from_user_dto(user: UserDTO, token: &str) -> Result<UserInfo, AppError> {
        match user.id {
            Some(id) => {

                    let passport_name = digest(user.clone().username.clone());

                    let passport_bytes = fs::read(&format!("data/{}.png", passport_name)).map_err(|err| {
                        AppError::new(
                            format!("Error reading passport. {}", err.to_string()).as_str(),
                            ErrorType::ValidationError,
                        )
                    })?;

                    let mime_type = tree_magic::from_u8(&passport_bytes);

                    if mime_type != "image/png" {
                        return Err(AppError::new("Passport has wrong file format!", ErrorType::Internal));
                    }

                    let base64_string = &base64::encode(&passport_bytes);
                    Ok(UserInfo {
                    user_id: id,
                    username: user.username,
                    displayname: user.displayname,
                    token: token.to_string(),
                    passport: base64_string.to_string()
                })
            },
            None => Err(AppError::new(
                "Error getting user id after login",
                ErrorType::Internal,
            )),
        }
    }
}


impl CurrentUserInfo {
    pub fn from_user_dto(user: UserDTO, token: &str) -> Result<CurrentUserInfo, AppError> {
        match user.id {
            Some(id) => {
                    Ok(CurrentUserInfo {
                    user_id: id,
                    username: user.username,
                    displayname: user.displayname,
                    token: token.to_string()
                })
            },
            None => Err(AppError::new(
                "Error getting user id after login",
                ErrorType::Internal,
            )),
        }
    }
}
