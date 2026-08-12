import type { MetadataRoute } from "next";
import { getPublishedPapers } from "@/lib/archive";

const SITE_URL = process.env.VERCEL_PROJECT_PRODUCTION_URL
  ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
  : "https://ugjcs.example";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const papers = await getPublishedPapers();
  return [
    { url: `${SITE_URL}/` },
    { url: `${SITE_URL}/search` },
    ...papers.map((paper) => ({ url: `${SITE_URL}/papers/${paper.tracking_code}` })),
  ];
}
