import { execFileSync } from "node:child_process";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const client = resolve(root, "packages/api-client");
const openapiPath = resolve(root, "docs/api/v1/openapi.json");
const typesPath = resolve(client, "src/generated.ts");
const check = process.argv.includes("--check");
const temp = mkdtempSync(resolve(tmpdir(), "vessel-openapi-"));

try {
  const command = process.env.API_PYTHON || "uv";
  const args = process.env.API_PYTHON
    ? ["-m", "duna.api.export_openapi"]
    : ["run", "python", "-m", "duna.api.export_openapi"];
  const schema = execFileSync(command, args, { cwd: root, encoding: "utf8" });
  const schemaTmp = resolve(temp, "openapi.json");
  const typesTmp = resolve(temp, "generated.ts");
  writeFileSync(schemaTmp, schema);
  execFileSync(
    resolve(client, "node_modules/.bin/openapi-typescript"),
    [schemaTmp, "-o", typesTmp],
    { cwd: root, stdio: "inherit" },
  );
  const generated = readFileSync(typesTmp, "utf8");
  if (check) {
    for (const [path, content] of [
      [openapiPath, schema],
      [typesPath, generated],
    ]) {
      if (readFileSync(path, "utf8") !== content) {
        throw new Error(`${path} is out of date; run pnpm api:generate`);
      }
    }
    console.log("OpenAPI schema and TypeScript types are up to date.");
  } else {
    mkdirSync(dirname(openapiPath), { recursive: true });
    writeFileSync(openapiPath, schema);
    writeFileSync(typesPath, generated);
    console.log("OpenAPI schema and TypeScript types generated.");
  }
} finally {
  rmSync(temp, { recursive: true, force: true });
}
