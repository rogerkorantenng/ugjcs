import { sealData, unsealData } from "iron-session";
import { describe, expect, it } from "vitest";
import type { SessionData } from "./session";

const PASSWORD = "a".repeat(32);

describe("session sealing", () => {
  it("round-trips user identity and tokens through the sealed cookie payload", async () => {
    const original: SessionData = {
      user: { id: "u1", email: "a@ug.edu.gh", roles: ["author"] },
      accessToken: "access-abc",
      refreshToken: "refresh-xyz",
      accessTokenExpiresAt: Date.now() + 900_000,
    };
    const sealed = await sealData(original, { password: PASSWORD });
    const restored = await unsealData<SessionData>(sealed, { password: PASSWORD });
    expect(restored).toEqual(original);
  });

  it("never recovers the original payload when unsealed with the wrong password", async () => {
    // iron-session@8's `unsealData` resolves to `{}` on a MAC/decryption failure rather
    // than rejecting (verified against the installed version) — so the meaningful
    // assertion is that the wrong password can never reconstruct the sealed session data,
    // not that a specific error is thrown.
    const original = { user: { id: "u1", email: "a@ug.edu.gh", roles: ["author"] } };
    const sealed = await sealData(original, { password: PASSWORD });
    const restored = await unsealData(sealed, { password: "b".repeat(32) });
    expect(restored).not.toEqual(original);
  });
});
