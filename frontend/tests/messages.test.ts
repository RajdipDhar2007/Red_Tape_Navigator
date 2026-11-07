import { describe, expect, it } from "vitest";
import en from "../messages/en.json";
import bn from "../messages/bn.json";
import hi from "../messages/hi.json";

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
});
