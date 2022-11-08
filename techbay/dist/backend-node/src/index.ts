import express, { Application } from "express";
import morgan from "morgan";
import ProfileController from "./controllers/profile.controller";
import RequestsController from "./controllers/requests.controller";
import TradingController from "./controllers/trading.controller";
import cors from "cors";

const app: Application = express();

app.use(cors());

app.use(express.json());
app.use(morgan("tiny"));

app.use("/profile", ProfileController);
app.use("/request", RequestsController);
app.use("/offer", TradingController);

app.listen(8080, () => {
    console.log("Server is running on port", 8080);
});
