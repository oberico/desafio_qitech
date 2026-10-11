import json

from jsonschema import Draft7Validator, validators

from errors.custom_errors import InvalidSchema

STRICT_INTEGER_CHECKER = Draft7Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, instance: isinstance(instance, int) and not isinstance(instance, bool)
)
StrictDraft7Validator = validators.extend(Draft7Validator, type_checker=STRICT_INTEGER_CHECKER)


def validate_json(payload: dict, schema_path: str) -> dict:
    with open(schema_path, encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    error = next(iter(StrictDraft7Validator(schema).iter_errors(payload)), None)
    if error is not None:
        location = ".".join(str(part) for part in error.absolute_path) or "body"
        raise InvalidSchema(f"{location}: {error.message}")

    return payload
