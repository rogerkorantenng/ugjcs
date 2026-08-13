import { NextResponse } from "next/server";
import { z } from "zod";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { AdminAccount } from "@/types/wave2";

const ActiveInput = z.object({
  is_active: z.boolean(),
});

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const parsed = ActiveInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "about:blank", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }
  try {
    const result = await authedFetch<AdminAccount | undefined>(`/admin/accounts/${id}/active`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    return result === undefined ? new NextResponse(null, { status: 204 }) : NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
