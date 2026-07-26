import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const serverRoot = path.resolve(__dirname, "../../");

for (const envFile of [".env.local", ".env.dev", ".env"]) {
  dotenv.config({ path: path.join(serverRoot, envFile) });
  dotenv.config({ path: path.resolve(process.cwd(), envFile) });
}

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "../../prisma/generated/prisma/client.js";

const rawDbUrl = process.env.DATABASE_URL;
const connectionString = (rawDbUrl && rawDbUrl !== "undefined")
  ? rawDbUrl
  : "postgresql://quickvoice:quickvoice@localhost:5433/quickvoice";

const adapter = new PrismaPg({ connectionString });
const prisma = new PrismaClient({ adapter });

export default prisma;