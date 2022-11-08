use crate::errors::AppError;
use crate::models::users::{
    CreateUserDTO, UserDTO
};
use diesel::expression_methods::ExpressionMethods;
use diesel::query_dsl::QueryDsl;
use diesel::r2d2::{ConnectionManager, PooledConnection};
use diesel::RunQueryDsl;
use diesel::PgConnection;

type Pooled = PooledConnection<ConnectionManager<PgConnection>>;

pub struct DBAccessManager {
    connection: Pooled,
}

impl DBAccessManager {
    pub fn new(connection: Pooled) -> DBAccessManager {
        DBAccessManager { connection }
    }

    pub fn create_user(&self, dto: CreateUserDTO) -> Result<UserDTO, AppError> {
        use super::schema::profiles;

        Ok(diesel::insert_into(profiles::table)
            .values(&dto)
            .get_result(&self.connection)
            .map_err(|err| AppError::from_diesel_err(err, "creating user"))?)
    }

    pub fn login(&self, username: String, password_hash: String) -> Result<UserDTO, AppError> {
        use super::schema::profiles;

        let r = profiles::table
            .filter(profiles::username.eq(&username))
            .filter(profiles::password.eq(&password_hash))
            .first::<UserDTO>(&self.connection)
            .map_err(|err| AppError::from_diesel_err(err, "logging in"))?;
        Ok(r)
    }

    pub fn get_user(&self, user_id: i32) -> Result<UserDTO, AppError> {
        use super::schema::profiles;

        profiles::table.filter(profiles::id.eq(&user_id)).first::<UserDTO>(&self.connection)
        .map_err( |err| {
            AppError::from_diesel_err(err, "getting user")
        })
    }
}
