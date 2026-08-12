import { describe, expect, it, vi, afterEach } from "vitest";
import { env } from "@/lib/env";

vi.mock("@/lib/session", () => ({
  getSession: vi.fn().mockResolvedValue({ accessToken: "token-123", user: { id: "u1", email: "a@ug.edu.gh", roles: ["author"] } }),
}));

afterEach(() => vi.restoreAllMocks());

describe("POST /api/manuscripts", () => {
  it("streams a multipart body upstream with a bearer header and the original content-type", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => ({ tracking_code: "UGJCS-2026-0099", status: "submitted" }),
    });
    vi.stubGlobal("fetch", fetchSpy);

    const { POST } = await import("./route");
    const formData = new FormData();
    formData.set("title", "A Paper Title");
    formData.set("abstract", "x".repeat(100));
    formData.set("keywords", "ir");
    formData.set("file", new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], "paper.pdf", { type: "application/pdf" }));
    const request = new Request("http://localhost/api/manuscripts", { method: "POST", body: formData });

    const response = await POST(request);

    expect(response.status).toBe(201);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    expect(url).toBe(`${env.API_BASE_URL}/manuscripts`);
    expect(init.headers.Authorization).toBe("Bearer token-123");
    expect(init.headers["Content-Type"]).toContain("multipart/form-data");
    expect(init.body).toBeDefined();
  });

  it("rejects a request that is not multipart before ever calling upstream", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const { POST } = await import("./route");
    const request = new Request("http://localhost/api/manuscripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "x" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
