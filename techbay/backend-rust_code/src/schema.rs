table! {
    profiles (id) {
        id -> Nullable<Integer>,
        username -> Text,
        password -> Text,
        displayname -> Text,
        address -> Nullable<Text>,
        is_address_public -> Bool,
        telephone_number -> Nullable<Text>,
        is_telephone_number_public -> Bool,
        status -> Nullable<Text>,
        is_status_public -> Bool,
    }
}

allow_tables_to_appear_in_same_query!(
    profiles,
);
