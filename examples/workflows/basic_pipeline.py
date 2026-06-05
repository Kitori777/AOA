"""Example workflow for the modular AOA stack.
Run: python examples/workflows/basic_pipeline.py
"""

from pathlib import Path

import pandas as pd

from AOA.core.mlstack.pipelines import WorkflowPipeline


def main() -> None:
    path = Path("data/sample/sample_table.csv")
    df = pd.read_csv(path)
    pipeline = WorkflowPipeline(test_size=0.2, random_state=42, backend="classic")
    result = pipeline.run(df, ["Quality", "Delay", "Schedule"])

    print("Train rows:", result.train_rows)
    print("Test rows:", result.test_rows)
    for line in result.metric_lines:
        print(line)


if __name__ == "__main__":
    main()
