import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, env } from "prisma/config";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
for (const envFile of [".env.local", ".env.dev", ".env"]) {
  dotenv.config({ path: path.join(__dirname, envFile) });
  dotenv.config({ path: path.resolve(process.cwd(), envFile) });
}

if (!process.env.DATABASE_URL) {
  process.env.DATABASE_URL = "postgresql://quickvoice:quickvoice@localhost:5433/quickvoice";
}

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
  },
  datasource: {
    url: env("DATABASE_URL"),
  },
});
