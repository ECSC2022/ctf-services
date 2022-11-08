import express from "express";
import {authMiddleware, parseAuthorizationHeaderIfAvailable} from "../middlewares/auth.middleware";
import * as tradingRepository from "../repositories/trading.repository";
import * as requestRepository from "../repositories/requests.repository";
import {NewOffer, Order} from "../types/trading.type";
import {RequestWithToken} from "../types/helper.type";
import {filetypename} from "magic-bytes.js";
import {body, oneOf, validationResult} from "express-validator";

const controller = express();

controller.get("", parseAuthorizationHeaderIfAvailable, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user?.userId;
        const pageConfig = {
            page: parseInt(req.query.page?.toString() ?? '0'),
            limit: parseInt(req.query.limit?.toString() ?? '10'),
            creationOrder: req.query.creationOrder?.toString() as Order ?? Order.ASC,
            nameOrder: req.query.nameOrder?.toString() as Order ?? Order.ASC,
        };
        const offers = await tradingRepository.getAllPaginated(pageConfig, userId);
        res.send(offers);
    } catch (e) {
        console.error("Get offers failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.get("/me", authMiddleware, async (req, res) => {
    try {
        const pageConfig = {
            page: parseInt(req.query.page?.toString() ?? '0'),
            limit: parseInt(req.query.limit?.toString() ?? '10'),
            creationOrder: req.query.creationOrder?.toString() as Order ?? Order.ASC,
            nameOrder: req.query.nameOrder?.toString() as Order ?? Order.ASC,
        };
        const userId = (req as unknown as RequestWithToken).user.userId;
        const offers = await tradingRepository.getOffersByUserId(userId, pageConfig);
        res.send(offers);
    } catch (e) {
        console.error("get own offers failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.get("/:offerId", parseAuthorizationHeaderIfAvailable, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user?.userId;
        const offerId = req.params.offerId;
        if (offerId == null || isNaN(parseInt(offerId))) {
            return res.sendStatus(400);
        }
        const offer = await tradingRepository.getOfferInfo(parseInt(offerId), userId);
        if (offer == null) {
            return res.sendStatus(404);
        }
        res.send(offer);
    } catch (e) {
        console.error("Get offer details failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

controller.post(
    "",
    authMiddleware,
    body('name').isString().isLength({min: 5}),
    body('description').isString().isLength({min: 10}),
    oneOf([body('picture').isEmpty(), body('picture').isString().isLength({max: 68267 /* length of 50kB in base64 encoding*/})]),
    async (req, res) => {
        try {
            if (!validationResult(req).isEmpty()) {
                return res.sendStatus(400);
            }

            const offer: NewOffer = req.body;
            const userId = (req as unknown as RequestWithToken).user.userId;

            if (offer.picture != undefined && offer.picture.trim().length > 0) {
                const buffer = Buffer.from(offer.picture, 'base64');
                if (buffer.length > 50 * 1024) {
                    return res.sendStatus(400);
                }
                const possibleFiletypes = new Set(filetypename([...buffer]));
                if (possibleFiletypes.has("png")) {
                    offer.picture = "data:image/png;base64," + offer.picture;
                } else if (possibleFiletypes.has("jpg")) {
                    offer.picture = "data:image/jpg;base64," + offer.picture;
                } else if (possibleFiletypes.has("gif")) {
                    offer.picture = "data:image/gif;base64," + offer.picture;
                } else {
                    return res.sendStatus(400);
                }
            }

            await tradingRepository.addNewOffer(userId, offer);
            res.sendStatus(200);
        } catch (e) {
            console.error("Add offer failed:");
            console.error(e);
            res.status(500).send({"error": e + ''});
        }
    });

controller.delete("/:offerId", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;

        const offerId = req.params.offerId;
        if (offerId == null || isNaN(parseInt(offerId))) {
            return res.sendStatus(400);
        }
        const offer = await tradingRepository.getOfferInfo(parseInt(offerId), userId);

        if (offer?.creator.userId != userId) {
            return res.sendStatus(404);
        }
        await requestRepository.deleteAllForOffer(parseInt(offerId));
        
        await tradingRepository.removeOffer(parseInt(offerId));
        res.sendStatus(200);
    } catch (e) {
        console.error("Delete offer failed:");
        console.error(e);
        res.status(500).send({"error": e + ''});
    }
});

export default controller;