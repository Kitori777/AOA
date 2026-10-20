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
  [path.join("examples", "esm_jobs_05_tight_deadlines.csv"), [6, 5]],
  [path.join("examples", "esm_jobs_06_component_wait.csv"), [7, 5]],
  [path.join("examples", "esm_jobs_07_parallel_balance.csv"), [8, 5]],
  [path.join("examples", "esm_jobs_08_changeovers.csv"), [9, 5]],
  [path.join("examples", "esm_jobs_09_urgent_mix.csv"), [10, 5]],
  [path.join("examples", "esm_jobs_10_mixed_constraints.csv"), [11, 14]],
  [path.join("examples", "esm_flow_10_three_machines.csv"), [11, 5]],
  [path.join("examples", "esm_flow_10_bottleneck.csv"), [11, 5]],
  [path.join("examples", "esm_flow_10_urgent.csv"), [11, 14]],
  ...["eco_trap", "component_wait", "intentional_idle", "multiple_optima", "blocked_components"]
    .map(name => [path.join("examples", `esm_flow_10_${name}.csv`), [11, 14]]),
  [path.join("examples", "esm_flow_06_ties.csv"), [7, 5]],
  [path.join("examples", "esm_flow_10_eight_machines.csv"), [11, 10]],
  [path.join("examples", "esm_flow_10_eco_components.csv"), [11, 14]],
  [path.join("article", "esm_paper_01.csv"), [4, 4]],
  [path.join("article", "esm_paper_02.csv"), [4, 4]],
  [path.join("article", "esm_paper_03.csv"), [4, 4]],
  [path.join("article", "esm_paper_04.csv"), [5, 4]],
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
    range: `A1:${String.fromCharCode(64 + columnCount)}${rowCount}`,
    maxChars: 1800,
  });
  if (!inspection.ndjson) {
    throw new Error(`${name}: artifact inspection returned no data`);
  }
  console.log(`${name}: OK ${rowCount - 1} rows x ${columnCount} columns`);
}
