import {Request, requestFromDb} from "../types/request.type";
import {getDbConnection} from "../db";

export async function requestOfferById(offerId: number, userId: number) {
    const conn = await getDbConnection();
    await conn.query("INSERT INTO requests (user_id, offer_id) VALUES ($1::integer, $2::integer)", [userId, offerId]);
}

export async function getRequestsForOffersOfUser(userId: number): Promise<Request[]> {
    const conn = await getDbConnection();
    const result  = await conn.query("SELECT r.id, r.user_id, r.offer_id, r.timestamp FROM requests r JOIN offers o ON r.offer_id = o.id WHERE o.creator_id = $1::integer", [userId]);
    return result.rows.map(requestFromDb);
}

export async function getRequestsMadeByUser(userId: number): Promise<Request[]> {
    const conn = await getDbConnection();
    const result  = await conn.query("SELECT * FROM requests WHERE user_id = $1::integer", [userId]);
    return result.rows.map(requestFromDb);
}

export async function getRequest(requestId: number): Promise<Request | undefined> {
    const conn = await getDbConnection();
    const result  = await conn.query("SELECT * FROM requests WHERE id = $1::integer", [requestId]);
    return result.rows.length > 0 ? requestFromDb(result.rows[0]) : undefined;
}

export async function isRequestFromUser(requestId: number, userId: number): Promise<boolean> {
    const conn = await getDbConnection();
    const result = await conn.query("SELECT exists(SELECT *  FROM requests WHERE id=$1::integer AND user_id=$2::integer)", [requestId, userId]);
    return result.rows[0].exists;
}

export async function isRequestForOfferOfUser(requestId: number, userId: number): Promise<boolean> {
    const conn = await getDbConnection();
    const result = await conn.query("SELECT exists(SELECT * FROM requests r JOIN offers o ON r.offer_id=o.id WHERE r.id = $1::integer AND o.creator_id = $2::integer)", [requestId, userId]);
    return result.rows[0].exists;
}

export async function acceptRequest(requestId: number) {
    const conn = await getDbConnection();
    try {
        await conn.query("BEGIN");
        const res = await conn.query("SELECT * FROM requests WHERE id=$1::integer", [requestId]);
        const request = res.rows[0];
        await conn.query("UPDATE offers SET owner_id=$1::integer WHERE id=$2::integer", [request.user_id, request.offer_id]);
        await conn.query("DELETE FROM requests WHERE offer_id=$1::integer", [request.offer_id]);
        await conn.query("COMMIT");
    } catch {
        await conn.query("ROLLBACK");
    }
}

export async function removeRequest(requestId: number) {
    const conn = await getDbConnection();
    await conn.query("DELETE FROM requests WHERE id=$1::integer", [requestId]);
}

export async function deleteAllForOffer(offerId: number): Promise<void> {
    const conn = await getDbConnection();
    await conn.query("DELETE FROM requests r WHERE r.offer_id = $1::integer", [offerId]);
}