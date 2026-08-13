import { NextResponse } from "next/server";
import { backendFetchText, ProblemDetailsError } from "@/lib/backend";

/**
 * Public proxy for `GET /archive/{code}/citation?format=bibtex|ris` (published papers
 * only, upstream). Streams the text/plain citation back with a `Content-Disposition`
 * attachment so the "BibTeX"/"RIS" buttons on the paper page are plain `<a href>`
 * downloads — no client JS, no token, same anonymous posture as the rest of
 * `/api/archive/*`.
 */
const EXTENSIONS = { bibtex: "bib", ris: "ris" } as const;

export async function GET(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const format = new URL(request.url).searchParams.get("format") ?? "bibtex";
  if (!(format in EXTENSIONS)) {
    return NextResponse.json(
      {
        type: "about:blank",
        title: "Unsupported citation format",
        status: 422,
        detail: "Supported formats are 'bibtex' and 'ris'.",
      },
      { status: 422 },
    );
  }
  try {
    const citation = await backendFetchText(`/archive/${trackingCode}/citation?format=${format}`, {
      next: { revalidate: 300 },
    });
    const extension = EXTENSIONS[format as keyof typeof EXTENSIONS];
    return new NextResponse(citation, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": `attachment; filename=${trackingCode}.${extension}`,
      },
    });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
