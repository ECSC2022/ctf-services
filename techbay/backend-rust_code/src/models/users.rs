use crate::{
    api_models::NewUser,
    schema::profiles,
};
use serde_derive::Serialize;

#[derive(Serialize, Debug, Clone, Queryable, AsChangeset)]
#[table_name = "profiles"]
pub struct UserDTO {
    pub id: Option<i32>,
    pub username: String,
    pub password: String,
    pub displayname: String,
    pub address: Option<String>,
    pub is_address_public: bool,
    pub telephone_number: Option<String>,
    pub is_telephone_number_public: bool,
    pub status: Option<String>,
    pub is_status_public: bool,
}

// Struct for creating Book
#[derive(Debug, Clone, Insertable)]
#[table_name = "profiles"]
pub struct CreateUserDTO {
    pub username: String,
    pub password: String,
    pub displayname: String,
    pub is_address_public: bool,
    pub is_telephone_number_public: bool,
    pub is_status_public: bool,
}

impl CreateUserDTO {
    pub fn from_new_user(user: NewUser) -> CreateUserDTO {
        CreateUserDTO {
            username: user.username.clone(),
            password: user.hashed_password,
            displayname: user.username,
            is_address_public: false,
            is_telephone_number_public: false,
            is_status_public: false
        }
    }
}