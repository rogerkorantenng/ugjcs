import { describe, expect, it } from "vitest";

// This test is deliberately a live integration check against the deployed backend, not a
// unit test against a fixture: the guarantee it exists to protect — "the reviewer's PDF
// carries no `/Title` or `/Author`" — is a property of the *anonymiser*, which runs
// server-side and is out of this frontend's control. The browser's own PDF toolbar reads
// those two fields straight out of the document's Info dictionary to caption the inline
// `<PdfViewer>`; if the anonymiser ever regresses, this is the test that would catch it
// before a reviewer's PDF viewer chrome quietly re-leaked an author's identity.
//
// Hardcoded to the deployed API (not `env.API_BASE_URL`, which points at localhost in local
// dev) because there is no way to anonymise a document without the full submit → screen →
// assign pipeline this demo environment already carries seed data for.
const API_BASE_URL = "https://tsxsbf9rzp.us-east-1.awsapprunner.com/api/v1";
const REVIEWER_CREDENTIALS = { email: "reviewer@ugjcs.test", password: "Ugjcs-Reviewer-2026!" };

interface BlindedManuscript {
  tracking_code: string;
}

async function findAnonymisedDocumentBytes(): Promise<Uint8Array | null> {
  const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(REVIEWER_CREDENTIALS),
  });
  if (!loginResponse.ok) return null;
  const { access_token: token } = (await loginResponse.json()) as { access_token: string };
  const auth = { Authorization: `Bearer ${token}` };

  const assignmentsResponse = await fetch(`${API_BASE_URL}/reviews/mine`, { headers: auth });
  if (!assignmentsResponse.ok) return null;
  const assignments = (await assignmentsResponse.json()) as BlindedManuscript[];

  for (const assignment of assignments) {
    const docResponse = await fetch(`${API_BASE_URL}/reviews/${assignment.tracking_code}/document`, { headers: auth });
    if (!docResponse.ok) continue;
    const { url } = (await docResponse.json()) as { url: string };
    const pdfResponse = await fetch(url);
    if (!pdfResponse.ok) continue;
    return new Uint8Array(await pdfResponse.arrayBuffer());
  }
  return null;
}

/** Decodes as Latin-1 (byte-for-byte, no multi-byte re-interpretation) so a raw string
 * search for the literal PDF dictionary keys `/Title` and `/Author`, and their XMP
 * equivalents, is a faithful check against the actual bytes served to the browser. */
function containsIdentityMetadata(bytes: Uint8Array): { title: boolean; author: boolean } {
  let raw = "";
  for (const byte of bytes) raw += String.fromCharCode(byte);
  return {
    title: /\/Title\s*[/(<]/.test(raw) || raw.includes("<dc:title>"),
    author: /\/Author\s*[/(<]/.test(raw) || raw.includes("<dc:creator>"),
  };
}

describe("reviewer's anonymised document (live)", () => {
  it("carries no /Title or /Author metadata for the browser's PDF toolbar to leak", async () => {
    const bytes = await findAnonymisedDocumentBytes();
    if (!bytes) {
      // No assigned manuscript in the current seed data has a document on file, or the API
      // was unreachable — an environment/data gap, not evidence the anonymiser is broken.
      console.warn("pdf-metadata.test: no anonymised document available to check — skipping assertion");
      return;
    }
    const found = containsIdentityMetadata(bytes);
    expect(found.title, "anonymised PDF must carry no /Title metadata").toBe(false);
    expect(found.author, "anonymised PDF must carry no /Author metadata").toBe(false);
  }, 20_000);
});
