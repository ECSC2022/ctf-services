import {NewOffer, Offer, PageConfig} from "../types/trading.type";
import {getDbConnection} from "../db";

export async function getAllPaginated(pageConfig: PageConfig, userId: number): Promise<Offer[]> {
    const conn = await getDbConnection();

    const res = await conn.query(
        "SELECT o.id as offerId, o.name as offerName, o.description as offerDescription, o.picture as offerPicture, o.timestamp as offerTimestamp, " +
        "c.id as creatorId, c.username as creatorUsername, c.displayname as creatorDisplayname, " +
        "ow.id as ownerId, ow.username as ownerUsername, ow.displayname as ownerDisplayname," +
        "(SELECT exists(SELECT * FROM requests r WHERE r.offer_id = o.id AND r.user_id = $1::integer)) as isRequestedByMe " +
        "FROM offers o " +
        "JOIN profiles c ON o.creator_id = c.id " +
        "LEFT JOIN profiles ow ON o.owner_id = ow.id "+safePagination(pageConfig), [userId]
    );
    const rows = res.rows;

    return rows.map(databaseOfferDataToOffer);
}

export async function getOfferInfo(offerId: number, userId: number): Promise<Offer | undefined> {
    const conn = await getDbConnection();
    const res = await conn.query(
        "SELECT o.id as offerId, o.name as offerName, o.description as offerDescription, o.picture as offerPicture, o.timestamp as offerTimestamp, " +
        "c.id as creatorId, c.username as creatorUsername, c.displayname as creatorDisplayname, " +
        "ow.id as ownerId, ow.username as ownerUsername, ow.displayname as ownerDisplayname," +
        "(SELECT exists(SELECT * FROM requests r WHERE r.offer_id = o.id AND r.user_id = $2::integer)) as isRequestedByMe " +
        "FROM offers o " +
        "JOIN profiles c ON o.creator_id = c.id " +
        "LEFT JOIN profiles ow ON o.owner_id = ow.id " +
        "WHERE o.id = $1::integer", [offerId, userId]
    );
    const rows = res.rows;
    if (rows.length == 0) {
        return;
    }

    return databaseOfferDataToOffer(rows[0]);
}

export async function getOffersByUserId(userId: number, pageConfig: PageConfig): Promise<Offer[]> {
    const conn = await getDbConnection();

    const res = await conn.query(
        "SELECT o.id as offerId, o.name as offerName, o.description as offerDescription, o.picture as offerPicture, o.timestamp as offerTimestamp, " +
        "c.id as creatorId, c.username as creatorUsername, c.displayname as creatorDisplayname, " +
        "ow.id as ownerId, ow.username as ownerUsername, ow.displayname as ownerDisplayname," +
        "(SELECT exists(SELECT * FROM requests r WHERE r.offer_id = o.id AND r.user_id = $2::integer)) as isRequestedByMe " +
        "FROM offers o " +
        "JOIN profiles c ON o.creator_id = c.id " +
        "LEFT JOIN profiles ow ON o.owner_id = ow.id " +
        "WHERE c.id = $1::integer "+safePagination(pageConfig), [userId, userId]
    );
    const rows = res.rows;

    return rows.map(databaseOfferDataToOffer);
}

export async function addNewOffer(userId: number, offer: NewOffer) {
    const conn = await getDbConnection();
    await conn.query("INSERT INTO offers (name, description, picture, creator_id) " +
        "VALUES ($1::text, $2::text, $3::text, $4::integer)",
        [offer.name, offer.description, offer.picture, userId]);
}

export async function removeOffer(offerId: number) {
    const conn = await getDbConnection();
    await conn.query("DELETE FROM offers WHERE id=$1::integer", [offerId]);
}

function databaseOfferDataToOffer(databaseOfferData: any): Offer {
    const offer: Offer = {
        id: databaseOfferData.offerid,
        name: databaseOfferData.offername,
        description: databaseOfferData.offerdescription,
        picture: databaseOfferData.offerpicture,
        timestamp: new Date(databaseOfferData.offertimestamp),
        isRequestedByMe: databaseOfferData.isrequestedbyme,
        creator: {
            userId: databaseOfferData.creatorid,
            username: databaseOfferData.creatorusername,
            displayname: databaseOfferData.creatordisplayname
        },
        owner: undefined
    };
    if (databaseOfferData.ownerid != null) {
        offer.owner = {
            userId: databaseOfferData.ownerid,
            username: databaseOfferData.ownerusername,
            displayname: databaseOfferData.ownerdisplayname,
        };
    }

    return offer as Offer;
}

function safePagination(pageConfig: PageConfig) {
    const offset = (pageConfig.page ?? 0) * (pageConfig.limit ?? 10);
    return `ORDER BY name ${pageConfig.nameOrder}, timestamp ${pageConfig.creationOrder} LIMIT ${pageConfig.limit} OFFSET ${offset}`;
}