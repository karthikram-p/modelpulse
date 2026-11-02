import pandas as pd


def profile_dataset(file_path: str) -> dict:
    df = pd.read_parquet(file_path)

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    statistics = df[numeric_columns].describe().round(2)

    profile = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": df.columns.tolist(),
        "missing_values": {
            column: int(count)
            for column, count in df.isnull().sum().items()
        },
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_statistics": statistics.to_dict(),
    }

    if "cnt" in df.columns:
        profile["target_summary"] = {
            "mean_rentals": round(float(df["cnt"].mean()), 2),
            "median_rentals": round(float(df["cnt"].median()), 2),
            "minimum_rentals": int(df["cnt"].min()),
            "maximum_rentals": int(df["cnt"].max()),
        }

    if "hr" in df.columns and "cnt" in df.columns:
        hourly = (
            df.groupby("hr")["cnt"]
            .mean()
            .round(2)
        )

        profile["average_rentals_by_hour"] = {
            str(hour): float(count)
            for hour, count in hourly.items()
        }

    return profile