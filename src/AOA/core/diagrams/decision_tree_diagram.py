import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


def prepare_decision_tree_data(df: pd.DataFrame):
    if df.shape[1] < 2:
        raise ValueError("Do wykresu DecisionTree potrzeba co najmniej 2 kolumn")

    target = df.columns[-1]
    X = df.drop(columns=[target]).copy()
    y = df[target].copy()

    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))

    if pd.api.types.is_numeric_dtype(y):
        y = y.fillna(y.mean())
        model = DecisionTreeRegressor(max_depth=3, random_state=42)
    else:
        y = y.astype(str)
        model = DecisionTreeClassifier(max_depth=3, random_state=42)

    model.fit(X, y)

    return {
        "model": model,
        "feature_names": list(X.columns),
        "target_name": target,
    }
