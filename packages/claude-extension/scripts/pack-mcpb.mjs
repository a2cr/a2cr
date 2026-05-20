import { spawnSync } from "node:child_process";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(packageRoot, "../..");
const buildRoot = join(packageRoot, "build", "mcpb");
const stagingDir = join(buildRoot, "staging");
const artifactsDir = join(buildRoot, "artifacts");
const manifest = JSON.parse(await readFile(join(packageRoot, "manifest.json"), "utf8"));
const outputFile = join(artifactsDir, `${manifest.name}-${manifest.version}.mcpb`);

await rm(buildRoot, { recursive: true, force: true });
await mkdir(stagingDir, { recursive: true });
await mkdir(artifactsDir, { recursive: true });

run("npm", ["run", "build"], { cwd: packageRoot });

await copyRequiredFiles();
run("npm", ["ci", "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund"], { cwd: stagingDir });
await keepRuntimePackageMetadataOnly();

run("npx", ["-y", "@anthropic-ai/mcpb@2.1.2", "validate", "manifest.json"], {
  cwd: stagingDir,
});
run("npx", ["-y", "@anthropic-ai/mcpb@2.1.2", "pack", ".", outputFile], {
  cwd: stagingDir,
});

console.log(`MCPB artifact: ${outputFile}`);

async function copyRequiredFiles() {
  await Promise.all([
    cp(join(packageRoot, "assets"), join(stagingDir, "assets"), { recursive: true }),
    cp(join(packageRoot, "dist"), join(stagingDir, "dist"), { recursive: true }),
    cp(join(packageRoot, "manifest.json"), join(stagingDir, "manifest.json")),
    cp(join(packageRoot, "package.json"), join(stagingDir, "package.json")),
    cp(join(packageRoot, "package-lock.json"), join(stagingDir, "package-lock.json")),
    cp(join(packageRoot, "README.md"), join(stagingDir, "README.md")),
    cp(join(repoRoot, "LICENSE"), join(stagingDir, "LICENSE")),
    cp(join(repoRoot, "NOTICE"), join(stagingDir, "NOTICE")),
  ]);
}

async function keepRuntimePackageMetadataOnly() {
  const packageJson = JSON.parse(await readFile(join(packageRoot, "package.json"), "utf8"));
  const runtimePackageJson = {
    name: packageJson.name,
    version: packageJson.version,
    private: packageJson.private,
    description: packageJson.description,
    type: packageJson.type,
    license: packageJson.license,
    engines: packageJson.engines,
    dependencies: packageJson.dependencies,
  };

  await writeFile(join(stagingDir, "package.json"), `${JSON.stringify(runtimePackageJson, null, 2)}\n`);
  await rm(join(stagingDir, "package-lock.json"), { force: true });
}

function run(command, args, options) {
  const result = spawnSync(commandName(command), args, {
    ...options,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}`);
  }
}

function commandName(command) {
  return process.platform === "win32" ? `${command}.cmd` : command;
}
