export interface ProfileInfo {
    id: number;
    username: string;
    displayname: string;
    address: string | undefined;
    telephoneNumber: string | undefined;
    status: string | undefined;
}

export function profileInfoFromDb(dbObject: any): ProfileInfo {
    return {
        id: dbObject.id,
        username: dbObject.username,
        displayname: dbObject.displayname,
        address: dbObject.address,
        telephoneNumber: dbObject.telephone_number,
        status: dbObject.status,
    }
}

export interface ProfileInfoCurrentUser {
    id: number;
    username: string;
    displayname: string;
    address: string;
    isAddressPublic: boolean;
    telephoneNumber: string;
    isTelephoneNumberPublic: boolean;
    status: string;
    isStatusPublic: boolean;
}

export function profileInfoCurrentUserFromDb(dbObject: any): ProfileInfoCurrentUser {
    return {
        id: dbObject.id,
        username: dbObject.username,
        displayname: dbObject.displayname,
        address: dbObject.address,
        isAddressPublic: dbObject.is_address_public,
        telephoneNumber: dbObject.telephone_number,
        isTelephoneNumberPublic: dbObject.is_telephone_number_public,
        status: dbObject.status,
        isStatusPublic: dbObject.is_status_public,
    }
}

export interface ProfileUpdateInfo {
    displayname: string;
    address: string;
    isAddressPublic: boolean;
    telephoneNumber: string;
    isTelephoneNumberPublic: boolean;
    status: string;
    isStatusPublic: boolean;
}