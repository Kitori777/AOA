import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const artifactToolPath = process.env.ARTIFACT_TOOL_PATH;
if (!artifactToolPath) {
  throw new Error("Set ARTIFACT_TOOL_PATH to artifact_tool.mjs before validation.");
}
const { Workbook } = await import(pathToFileURL(artifactToolPath));

const sampleDir = path.resolve("data", "sample");
const expected = new Map([
  ["production.csv", [801, 51]],
  ["train.csv", [641, 51]],
  ["test.csv", [161, 51]],
  ["sample_table.csv", [13, 51]],
  ["bom.csv", [49, 5]],
  ["inventory.csv", [28, 8]],
  ["schedule.csv", [13, 32]],
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
    range: `A1:${name === "schedule.csv" ? "AF6" : name === "inventory.csv" ? "H4" : name === "bom.csv" ? "E4" : "F4"}`,
    maxChars: 1800,
  });
  if (!inspection.ndjson) {
    throw new Error(`${name}: artifact inspection returned no data`);
  }
  console.log(`${name}: OK ${rowCount - 1} rows x ${columnCount} columns`);
}
