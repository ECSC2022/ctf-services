import jwt from "jsonwebtoken";
import express from "express";
import {PRIVATE_KEY} from "../config";

export function authMiddleware(req: express.Request, res: express.Response, next: express.NextFunction) {
    const header = req.header("Authorization");

    if (header == null || header.length == 0) {
        return res.status(401).send({"error": "Unauthorized"});
    }
    const token = header?.replace("Bearer ", "") ?? '';
    const decoded = jwt.verify(token, PRIVATE_KEY);

    if (decoded == null || (decoded as any)?.user == null) {
        return res.status(401).send({"error": "Unauthorized"});
    }

    (req as any).user = (decoded as any).user;

    next();
}

export function authMiddleware2(req: express.Request, res: express.Response, next: express.NextFunction) {
    const header = req.header("Authorization");

    if (header == null || header.length == 0) {
        return res.status(401).send({"error": "Unauthorized"});
    }
    const token = header?.replace("Bearer ", "") ?? '';
    const payload = token.split(".")[1];
    try {
        (req as any).user = JSON.parse(Buffer.from(payload, 'base64').toString()).user;
    } catch {
        return res.status(401).send({"error": "Unauthorized"});
    }

    next();
}

export function parseAuthorizationHeaderIfAvailable(req: express.Request, res: express.Response, next: express.NextFunction) {
    const header = req.header("Authorization");
    if (header == null || header.length == 0) {
        return next();
    }

    const token = header?.replace("Bearer ", "") ?? '';
    const decoded = jwt.verify(token, PRIVATE_KEY);

    if (decoded == null) {
        return next();
    }

    (req as any).user = decoded;
    next();
}