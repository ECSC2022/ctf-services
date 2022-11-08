import express from "express";
import {authMiddleware} from "../middlewares/auth.middleware";
import * as requestsRepository from "../repositories/requests.repository";
import {RequestWithToken} from "../types/helper.type";

const controller = express();

controller.post("/:offerId", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;
        const offerId = req.params.offerId;
        if (offerId == null || isNaN(parseInt(offerId))) {
            return res.sendStatus(400);
        }

        await requestsRepository.requestOfferById(parseInt(offerId), userId);
        res.sendStatus(200);
    } catch (e) {
            console.error("Request offer by id failed:");
            console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.get("/others", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId
        const requests = await requestsRepository.getRequestsForOffersOfUser(userId);
        res.send(requests);
    } catch (e) {
        console.error("REquest for offers of user failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.get("/me", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;
        const requests = await requestsRepository.getRequestsMadeByUser(userId);
        res.send(requests);
    } catch (e) {
        console.error("Get requests made by user failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.post("/others/:requestId", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;
        const requestId = req.params.requestId;
        if (requestId == null || isNaN(parseInt(requestId))) {
            return res.sendStatus(400);
        }

        const canUserAcceptRequest = await requestsRepository.isRequestForOfferOfUser(parseInt(requestId), userId);
        if (!canUserAcceptRequest) {
            return res.sendStatus(404);
        }

        await requestsRepository.acceptRequest(parseInt(requestId));
        res.sendStatus(200);
    } catch (e) {
        console.error("Accept request failed failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.delete("/others/:requestId", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;
        const requestId = req.params.requestId;
        if (requestId == null || isNaN(parseInt(requestId))) {
            return res.sendStatus(400);
        }

        const requestForOfferOfCurrentUser = await requestsRepository.isRequestForOfferOfUser(parseInt(requestId), userId);
        if (!requestForOfferOfCurrentUser) {
            return res.sendStatus(404);
        }

        await requestsRepository.removeRequest(parseInt(requestId));
        res.sendStatus(200);
    } catch (e) {
        console.error("Remove request failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.delete("/me/:requestId", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;
        const requestId = req.params.requestId;
        if (requestId == null || isNaN(parseInt(requestId))) {
            return res.sendStatus(400);
        }
        const requestFromCurrentUser = await requestsRepository.isRequestFromUser(parseInt(requestId), userId);
        if (!requestFromCurrentUser) {
            return res.sendStatus(404);
        }

        await requestsRepository.removeRequest(parseInt(requestId));
        res.sendStatus(200);
    } catch (e) {
        console.error("Remove own request failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

export default controller;