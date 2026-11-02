import pandas as pd


REQUIRED_COLUMNS = [
    "instant",
    "dteday",
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
    "casual",
    "registered",
    "cnt",
]

NUMERIC_COLUMNS = [
    column for column in REQUIRED_COLUMNS
    if column != "dteday"
]


def validate_dataset(df: pd.DataFrame) -> dict:
    errors = []

    # 1. Check required columns
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        return {
            "valid": False,
            "errors": [f"Missing required columns: {missing_columns}"],
            "row_count": len(df),
        }

    # 2. Check missing values
    missing_values = df[REQUIRED_COLUMNS].isnull().sum()
    missing_columns_with_nulls = missing_values[
        missing_values > 0
    ]

    if not missing_columns_with_nulls.empty:
        errors.append(
            f"Missing values: {missing_columns_with_nulls.to_dict()}"
        )

    # 3. Check numeric data types
    numeric_data = {}

    for column in NUMERIC_COLUMNS:
        converted = pd.to_numeric(df[column], errors="coerce")
        numeric_data[column] = converted

        invalid_mask = df[column].notna() & converted.isna()

        if invalid_mask.any():
            errors.append(
                f"Column '{column}' contains non-numeric values."
            )

    # 4. Validate date format
    parsed_dates = pd.to_datetime(
        df["dteday"],
        errors="coerce",
    )

    invalid_dates = df["dteday"].notna() & parsed_dates.isna()

    if invalid_dates.any():
        errors.append("Column 'dteday' contains invalid dates.")

    # 5. Validate allowed ranges
    range_rules = {
        "season": (1, 4),
        "yr": (0, 1),
        "mnth": (1, 12),
        "hr": (0, 23),
        "holiday": (0, 1),
        "weekday": (0, 6),
        "workingday": (0, 1),
        "weathersit": (1, 4),
        "temp": (0, 1),
        "atemp": (0, 1),
        "hum": (0, 1),
        "windspeed": (0, 1),
        "casual": (0, None),
        "registered": (0, None),
        "cnt": (0, None),
    }

    for column, (minimum, maximum) in range_rules.items():
        values = numeric_data[column]

        if values.notna().sum() != df[column].notna().sum():
            continue

        if minimum is not None and (values < minimum).any():
            errors.append(
                f"Column '{column}' contains values below {minimum}."
            )

        if maximum is not None and (values > maximum).any():
            errors.append(
                f"Column '{column}' contains values above {maximum}."
            )

    # 6. Check unique record identifiers
    if numeric_data["instant"].notna().all():
        if numeric_data["instant"].duplicated().any():
            errors.append(
                "Column 'instant' contains duplicate identifiers."
            )

    # 7. Verify total rentals
    total_matches = (
        numeric_data["casual"] + numeric_data["registered"]
    )

    valid_totals = (
        total_matches.notna()
        & numeric_data["cnt"].notna()
    )

    if valid_totals.any():
        mismatch = (
            total_matches[valid_totals]
            != numeric_data["cnt"][valid_totals]
        )

        if mismatch.any():
            errors.append(
                "Column 'cnt' must equal 'casual' + 'registered'."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "row_count": len(df),
        "duplicate_count": int(
            numeric_data["instant"].duplicated().sum()
        ),
        "missing_value_count": int(
            df[REQUIRED_COLUMNS].isnull().sum().sum()
        ),
    }