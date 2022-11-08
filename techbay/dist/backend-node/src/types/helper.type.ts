import express from "express";
import {UserInfo} from "./trading.type";

export type RequestWithToken = express.Request & {user: UserInfo};