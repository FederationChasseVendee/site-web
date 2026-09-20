import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://federationchassevendee.github.io",
  base: "/site-web",
  output: "static",
  trailingSlash: "always",
});
