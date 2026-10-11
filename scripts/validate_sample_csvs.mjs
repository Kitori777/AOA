import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const artifactToolPath = process.env.ARTIFACT_TOOL_PATH;
if (!artifactToolPath) {
  throw new Error("Set ARTIFACT_TOOL_PATH to artifact_tool.mjs before validation.");
}
const { Workbook } = await import(pathToFileURL(artifactToolPath));

const sampleDir = path.resolve("data", "esm");
const expected = new Map([
  ["esm_jobs.csv", [5, 3]],
  [path.join("examples", "esm_jobs_05_tight_deadlines.csv"), [6, 11]],
  [path.join("examples", "esm_jobs_06_component_wait.csv"), [7, 11]],
  [path.join("examples", "esm_jobs_07_parallel_balance.csv"), [8, 11]],
  [path.join("examples", "esm_jobs_08_changeovers.csv"), [9, 11]],
  [path.join("examples", "esm_jobs_09_urgent_mix.csv"), [10, 11]],
  [path.join("examples", "esm_jobs_10_mixed_constraints.csv"), [11, 11]],
]);

for (const [name, dimensions] of expected) {
  const csvText = await fs.readFile(path.join(sampleDir, name), "utf8");
  const workbook = await Workbook.fromCSV(csvText, { sheetName: "Data" });
  const sheet = workbook.worksheets.getItem("Data");
  const values = sheet.getUsedRange(true).values;
  const rowCount = values.length;
  const columnCount = values[0]?.length ?? 0;
  if (rowCount !== dimensions[0] || columnCount !== dimensions[1]) {
    throw new Error(
      `${name}: expected ${dimensions[0]}x${dimensions[1]}, got ${rowCount}x${columnCount}`,
    );
  }
  const inspection = await workbook.inspect({
    kind: "region",
    sheetId: "Data",
    range: `A1:${columnCount === 3 ? "C" : "K"}${rowCount}`,
    maxChars: 1800,
  });
  if (!inspection.ndjson) {
    throw new Error(`${name}: artifact inspection returned no data`);
  }
  console.log(`${name}: OK ${rowCount - 1} rows x ${columnCount} columns`);
}
