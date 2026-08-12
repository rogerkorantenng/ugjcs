import { describe, expect, it, vi, afterEach } from "vitest";

vi.mock("@/lib/session", () => ({
  getSession: vi.fn().mockResolvedValue({ accessToken: "token-123", user: { id: "u1", email: "a@ug.edu.gh", roles: ["author"] } }),
}));

afterEach(() => vi.restoreAllMocks());

describe("POST /api/manuscripts", () => {
  it("forwards a validated JSON body upstream with a bearer header", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => ({ tracking_code: "UGJCS-2026-0099", status: "submitted" }),
    });
    vi.stubGlobal("fetch", fetchSpy);

    const { POST } = await import("./route");
    const request = new Request("http://localhost/api/manuscripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "A Paper Title", abstract: "x".repeat(100), keywords: ["ir"] }),
    });

    const response = await POST(request);

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer token-123");
    expect(JSON.parse(init.body as string)).toMatchObject({ title: "A Paper Title", co_author_ids: [] });
  });

  it("rejects a body that fails validation before ever calling upstream", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const { POST } = await import("./route");
    const request = new Request("http://localhost/api/manuscripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "short", abstract: "too short", keywords: [] }),
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
