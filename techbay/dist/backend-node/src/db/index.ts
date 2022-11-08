import {Client} from "pg";

let connected = false;
const client = new Client({
    host: process.env.DB_HOST ?? 'localhost',
    port: parseInt(process.env.DB_PORT ?? '5432'),
    database: process.env.DB_NAME ?? 'techbay',
    user: process.env.DB_USER ?? 'postgres',
    password: process.env.DB_PASSWORD ?? 'password',
});

export async function getDbConnection() {
    if (!connected) {
        connected = true;
        await client.connect();
    }
    return client;
}