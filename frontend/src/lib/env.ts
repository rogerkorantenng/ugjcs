import "server-only";
import { z } from "zod";

const EnvSchema = z.object({
  API_BASE_URL: z.string().url(),
  SESSION_SECRET: z.string().min(32, "SESSION_SECRET must be at least 32 characters"),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});

/**
 * Parsed once at import time. A missing or malformed variable must fail the build/boot,
 * not surface as a confusing runtime error three requests later.
 */
export const env = EnvSchema.parse({
  API_BASE_URL: process.env.API_BASE_URL,
  SESSION_SECRET: process.env.SESSION_SECRET,
  NODE_ENV: process.env.NODE_ENV,
});
