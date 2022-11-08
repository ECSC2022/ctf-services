import express from "express";
import {authMiddleware, authMiddleware2} from "../middlewares/auth.middleware";
import * as profileRepository from "../repositories/profile.repository";
import {RequestWithToken} from "../types/helper.type";
import {constants} from "http2";
import {body, validationResult} from "express-validator";


const controller = express();

controller.get("/", authMiddleware, async (req, res) => {
    try {
        const userId = (req as unknown as RequestWithToken).user.userId;
        const profile = await profileRepository.getProfileCurrentUserById(userId);
        if (profile == undefined) {
            return res.sendStatus(404);
        }
        res.send(profile);
    } catch (e) {
        console.error("Get profile of current user failed:");
        console.error(e);
        res.status(500).send({"error": e+''});
    }
});


controller.get("/:userId", async (req, res) => {
    try {
        const userId = req.params.userId;
        if (userId == null || isNaN(parseInt(userId))) {
            return res.sendStatus(constants.HTTP_STATUS_BAD_REQUEST);
        }
        const profile = await profileRepository.getProfileById(parseInt(userId));
        if (profile == undefined) {
            return res.sendStatus(404);
        }
        res.send(profile);
    } catch (e) {
        console.error("Get profile failed:");
        console.error(e);
        res.status(500).send({"error": e+''});
    }
});

controller.post(
    "/",
    authMiddleware,
    body('displayname').isString().isLength({min: 5}),
    body('address').isString(),
    body('isAddressPublic').isBoolean(),
    body('telephoneNumber').isString(),
    body('isTelephoneNumberPublic').isBoolean(),
    body('status').isString(),
    body('isStatusPublic').isBoolean(),
    async (req, res) => {
        if (!validationResult(req).isEmpty()) {
            return res.sendStatus(400);
        }

        const userId = (req as unknown as RequestWithToken).user.userId;

        try {
            await profileRepository.updateProfile(userId, req.body);
            res.sendStatus(200);
        } catch (e) {
            console.error("Update profile failed:");
            console.error(e);
            res.status(500).send({"error": e+''});
        }
    });

controller.post(
    "/status/visbility",
    authMiddleware2,
    body('visibility').isBoolean(),
    async (req, res) => {
        if (!validationResult(req).isEmpty()) {
            return res.sendStatus(400);
        }

        const userId = (req as unknown as RequestWithToken).user.userId;
        const profile = await profileRepository.getProfileCurrentUserById(userId);
        if (profile == null) {
            return res.sendStatus(404);
        }

        try {
            await profileRepository.updateProfile(userId, {
                ...profile,
                isStatusPublic: req.body.visibility,
            });
            res.sendStatus(200);
        } catch (e) {
            console.error("Update profile visibility failed:");
            console.error(e);
            res.status(500).send({"error": e+''});
        }
    })

export default controller;
