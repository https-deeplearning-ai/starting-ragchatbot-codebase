import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", "backend/**"] },
  js.configs.recommended,
  {
    files: ["frontend/**/*.js"],
    languageOptions: { sourceType: "script", globals: { ...globals.browser, marked: "readonly" } },
  },
];
