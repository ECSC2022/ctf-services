import {getDbConnection} from "../db";
import {
    ProfileInfo,
    ProfileInfoCurrentUser,
    profileInfoCurrentUserFromDb,
    profileInfoFromDb,
    ProfileUpdateInfo
} from "../types/profile.type";


export async function getProfileById(id: number): Promise<ProfileInfo | undefined> {
    const conn = await getDbConnection();
    const res = await conn.query("SELECT id, username, displayname, " +
        "CASE WHEN is_address_public THEN address ELSE null END as address," +
        "CASE WHEN is_status_public THEN status ELSE null END as status," +
        "CASE WHEN is_telephone_number_public THEN telephone_number ELSE null END as telephone_number " +
        "FROM profiles WHERE id=$1::int", [id]);
    const rows = res.rows;
    if (rows.length == 0) {
        return;
    }
    return profileInfoFromDb(res.rows[0]);
}

export async function getProfileCurrentUserById(id: number): Promise<ProfileInfoCurrentUser | undefined> {
    const conn = await getDbConnection();
    const res = await conn.query("SELECT * FROM profiles WHERE id=$1::int", [id]);
    const rows = res.rows;
    if (rows.length == 0) {
        return;
    }
    return profileInfoCurrentUserFromDb(res.rows[0]);
}

export async function updateProfile(id: number, updateInfo: ProfileUpdateInfo): Promise<void> {
    const conn = await getDbConnection();
    await conn.query("UPDATE profiles SET " +
        "displayname=$1::text, " +
        "address=$2::text, " +
        "is_address_public=$3::boolean, " +
        "telephone_number=$4::text, " +
        "is_telephone_number_public=$5::boolean, " +
        "status=$6::text, " +
        "is_status_public=$7::boolean " +
        "WHERE id=$8::integer",
        [
            updateInfo.displayname,
            updateInfo.address,
            updateInfo.isAddressPublic,
            updateInfo.telephoneNumber,
            updateInfo.isTelephoneNumberPublic,
            updateInfo.status,
            updateInfo.isStatusPublic,
            id
        ]);
}