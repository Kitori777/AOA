# Modularny Workflow (mlstack)

Nowa warstwa `AOA.core.mlstack` porzadkuje logike podobnie do bibliotek scikit:

- `models` - jednolity interfejs `fit/predict/score/export`
- `pipelines` - gotowy przeplyw: dane -> trening -> metryki
- `evaluation` - benchmarki k-fold
- `visual` - lekkie formatowanie raportow dla uzytkownika

## Szybki start

```python
from AOA.core.mlstack.pipelines import WorkflowPipeline

pipeline = WorkflowPipeline(test_size=0.2, random_state=42, backend="classic")
result = pipeline.run(df, ["Quality", "Delay", "Schedule"])
print(result.metric_lines)
```

## Benchmark modeli

```python
from AOA.core.mlstack.evaluation import run_benchmark
rows = run_benchmark(df, ["Quality", "Quality_ET", "Quality_GB"], folds=5)
```

## Praktyka

- Uzywaj `ModelRegistry`, gdy chcesz dynamicznie budowac modele po nazwie.
- Uzywaj `WorkflowPipeline`, gdy chcesz powtarzalny trening i raport metryk.
- Warstwa mlstack nie psuje starego API (`AOA.core.services.*`) i dziala obok niego.
