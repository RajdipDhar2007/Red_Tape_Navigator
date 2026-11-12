import { describe, expect, it } from "vitest";
import en from "../messages/en.json";
import bn from "../messages/bn.json";
import hi from "../messages/hi.json";
import {
  ApiError,
  clearTokens,
  del,
  formatFileSize,
  hasToken,
  patch,
  setTokens,
  uploadForm,
  validateVaultFile,
  VAULT_ALLOWED_TYPES,
  VAULT_DEFAULT_MAX_BYTES,
} from "../lib/api";

type Tree = { [k: string]: string | Tree };
const flat = (o: Tree, p = ""): string[] =>
  Object.entries(o).flatMap(([k, v]) => (typeof v === "string" ? [`${p}${k}`] : flat(v, `${p}${k}.`)));
const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");

describe("i18n catalogues", () => {
  const keys = flat(en as Tree).sort();
  for (const [name, m] of [["bn", bn], ["hi", hi]] as const) {
    it(`${name} has exactly the same keys as en`, () => {
      expect(flat(m as Tree).sort()).toEqual(keys);
    });
    it(`${name} keeps ICU placeholders`, () => {
      const get = (o: Tree, path: string) => path.split(".").reduce<string | Tree>((a, k) => (a as Tree)[k], o) as string;
      for (const k of keys) expect(placeholders(get(m as Tree, k))).toBe(placeholders(get(en as Tree, k)));
    });
  }
  it("every string is non-empty", () => {
    for (const m of [en, bn, hi]) {
      const get = (path: string) => path.split(".").reduce<string | Tree>((a, k) => (a as Tree)[k], m as Tree) as string;
      for (const k of keys) expect(get(k).trim().length).toBeGreaterThan(0);
    }
  });
  it("includes complete DPDP privacy self-service translation keys", () => {
    const requiredPrivacyKeys = [
      "privacy.export",
      "privacy.exportHelp",
      "privacy.consentsHeading",
      "privacy.purpose_service",
      "privacy.purpose_reminders",
      "privacy.purpose_identity_providers",
      "privacy.sessionsHeading",
      "privacy.deleteSessionBtn",
      "privacy.deleteSessionConfirm",
      "privacy.dangerHeading",
      "privacy.deleteTypeLabel",
      "privacy.deleteConfirmBtn",
    ];
    for (const k of requiredPrivacyKeys) {
      expect(keys).toContain(k);
    }
  });
  it("includes complete Document Vault translation keys across en, hi, and bn", () => {
    const requiredVaultKeys = [
      "nav.documents",
      "dash.documentsTitle",
      "dash.documentsHelp",
      "dash.documentsOpen",
      "documents.title",
      "documents.intro",
      "documents.uploadBtn",
      "documents.dropHint",
      "documents.guidance",
      "documents.downloadBtn",
      "documents.deleteBtn",
      "documents.deleteConfirmBtn",
      "documents.emptyTitle",
      "documents.errTooLarge",
      "documents.errUnsupported",
      "documents.scanNoticeDisabled",
    ];
    for (const k of requiredVaultKeys) {
      expect(keys).toContain(k);
    }
  });
  it("includes Help & Support, session management, reminder lifecycle, and admin readiness keys", () => {
    const requiredWorkflowKeys = [
      "nav.help",
      "help.title",
      "help.searchLabel",
      "help.catAll",
      "help.catGettingStarted",
      "help.catResults",
      "help.catPrivacy",
      "help.catDocuments",
      "help.catTroubleshooting",
      "help.q_what_h",
      "help.q_ai_h",
      "help.q_submit_h",
      "help.q_dpdp_h",
      "help.q_vault_h",
      "help.contactHeading",
      "help.contactUnconfigured",
      "dash.notFoundTitle",
      "dash.renameBtn",
      "dash.renameSave",
      "interview.backToChecklist",
      "done.backToReview",
      "done.channelLive",
      "done.channelMock",
      "done.statusScheduled",
      "done.cancelReminder",
      "staff.readinessHeading",
      "staff.purgeBtn",
    ];
    for (const k of requiredWorkflowKeys) {
      expect(keys).toContain(k);
    }
  });
});

describe("api client helpers", () => {
  it("extracts ApiError code and message and exposes del helper", () => {
    const err = new ApiError(409, { code: "goal_incomplete", message: "Please specify city" });
    expect(err.status).toBe(409);
    expect(err.code).toBe("goal_incomplete");
    expect(err.message).toBe("Please specify city");
    expect(typeof del).toBe("function");
    expect(typeof patch).toBe("function");
    expect(typeof uploadForm).toBe("function");
    clearTokens();
    expect(hasToken()).toBe(false);
    setTokens("a", "r");
  });

  it("validates Document Vault files and formats file sizes safely", () => {
    expect(VAULT_ALLOWED_TYPES).toEqual(["application/pdf", "image/png", "image/jpeg"]);
    expect(formatFileSize(0)).toBe("0 B");
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.00 MB");

    expect(validateVaultFile({ name: "rent.pdf", type: "application/pdf", size: 1024 })).toEqual({ ok: true });
    expect(validateVaultFile({ name: "photo.png", type: "image/png", size: 4096 })).toEqual({ ok: true });
    expect(validateVaultFile({ name: "id.jpg", type: "image/jpeg", size: 4096 })).toEqual({ ok: true });
    expect(validateVaultFile({ name: "empty.pdf", type: "application/pdf", size: 0 })).toEqual({
      ok: false,
      code: "empty",
    });
    expect(
      validateVaultFile({ name: "huge.pdf", type: "application/pdf", size: VAULT_DEFAULT_MAX_BYTES + 1 }),
    ).toEqual({
      ok: false,
      code: "too_large",
    });
    expect(validateVaultFile({ name: "payload.exe", type: "application/x-msdownload", size: 1024 })).toEqual({
      ok: false,
      code: "unsupported",
    });
    expect(validateVaultFile({ name: "trick.pdf.exe", type: "application/pdf", size: 1024 })).toEqual({
      ok: false,
      code: "unsupported",
    });
  });
});
