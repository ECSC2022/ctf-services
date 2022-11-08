export interface NewOffer {
    name: string;
    description: string;
    picture: string | undefined;
}

export interface Offer {
    id: number;
    name: string;
    description: string;
    picture: string;
    timestamp: Date;
    isRequestedByMe: boolean;
    creator: UserInfo;
    owner: UserInfo | undefined;
}

export interface UserInfo {
    userId: number;
    username: string;
    displayname: string;
}

export interface PageConfig {
    page: number | undefined;
    nameOrder: Order | undefined;
    creationOrder: Order | undefined;
    limit: number | undefined;
}

export enum Order {
    ASC = 'asc',
    DESC = 'desc'
}