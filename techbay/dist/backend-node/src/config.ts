import * as fs from "fs";

export const PRIVATE_KEY = fs.existsSync("private.key") ? fs.readFileSync("private.key", 'utf-8') : '53cr3t_k3y'