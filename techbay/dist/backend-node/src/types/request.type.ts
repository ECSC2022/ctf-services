export interface Request {
    id: number;
    userId: number;
    offerId: number;
    timestamp: Date;
}

export function requestFromDb(dbObject: any): Request {
    return {
        id: dbObject.id,
        userId: dbObject.user_id,
        offerId: dbObject.offer_id,
        timestamp: new Date(dbObject.timestamp),
    }
}