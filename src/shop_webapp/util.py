def validate_schema(data, schema):
    """
    Validates a data dict against a schema dict of types.
    Raises TypeError if types don't match.
    Raises KeyError if a required field is missing.
    """
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")

    for key, expected_type in schema.items():
        # 1. Check if the key exists
        if key not in data:
            raise KeyError(f"Missing required field: '{key}'")

        value = data[key]

        # 2. If the schema specifies a nested dict, recurse
        if isinstance(expected_type, dict):
            validate_schema(value, expected_type)

        # 3. Otherwise, check the type directly
        elif not isinstance(value, expected_type):
            raise TypeError(
                f"Field '{key}' expected {expected_type.__name__}, "
                f"got {type(value).__name__} (value: {value})"
            )

    return True
