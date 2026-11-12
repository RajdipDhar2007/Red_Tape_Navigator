import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Red Tape Navigator",
    short_name: "Red Tape",
    description: "Find the licences your business needs, fill the forms, and track renewals. Free. Guidance, not legal advice.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#183274",
    icons: [{ src: "/icon.svg", type: "image/svg+xml", sizes: "any" }],
  };
}
