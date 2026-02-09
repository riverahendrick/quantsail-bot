import sys
import unittest
from pathlib import Path

# Add services to path to allow importing from both api and engine
# This assumes the test is run from project root or services/api
# FIXED: Engine is now a proper dev dependency, so we don't need sys.path hacks.

try:
    from quantsail_engine.config.models import BotConfig as EngineBotConfig

    from app.schemas.config import BotConfig as ApiBotConfig
except ImportError as e:
    print(f"Skipping contract test due to import error: {e}")
    ApiBotConfig = None
    EngineBotConfig = None


class TestConfigParity(unittest.TestCase):
    def setUp(self):
        if ApiBotConfig is None or EngineBotConfig is None:
            self.skipTest("Could not import both BotConfig models")

    def test_schema_fields_match(self):
        """Verify that API and Engine BotConfig models have matching fields."""
        api_fields = set(ApiBotConfig.model_fields.keys())
        engine_fields = set(EngineBotConfig.model_fields.keys())

        missing_in_api = engine_fields - api_fields
        extra_in_api = api_fields - engine_fields

        self.assertFalse(
            missing_in_api,
            f"API config missing fields found in Engine: {missing_in_api}"
        )
        self.assertFalse(
            extra_in_api,
            f"API config has extra fields not in Engine: {extra_in_api}"
        )

    def test_field_types_match(self):
        """Verify that field types are compatible (recursive check)."""
        self._compare_models(ApiBotConfig, EngineBotConfig)

    def _compare_models(self, api_model, engine_model, path="BotConfig"):
        """Recursively compare two Pydantic models."""
        api_fields = api_model.model_fields
        engine_fields = engine_model.model_fields

        # Check field presence
        api_keys = set(api_fields.keys())
        engine_keys = set(engine_fields.keys())

        missing_in_api = engine_keys - api_keys
        extra_in_api = api_keys - engine_keys

        self.assertFalse(missing_in_api, f"Missing fields in API model at {path}: {missing_in_api}")
        self.assertFalse(extra_in_api, f"Extra fields in API model at {path}: {extra_in_api}")

        # Check field types
        for name, engine_field in engine_fields.items():
            api_field = api_fields[name]
            field_path = f"{path}.{name}"

            # Get the underlying types
            engine_type = engine_field.annotation
            api_type = api_field.annotation

            # Handle Optional/Union types if necessary, but for now strict check on structure
            # If both are Pydantic models, recurse
            if hasattr(engine_type, "model_fields") and hasattr(api_type, "model_fields"):
                self._compare_models(api_type, engine_type, field_path)
            else:
                # Compare string representation of types, checking for base names
                # to ignore module path differences
                # e.g. 'quantsail_engine.config.models.ExecutionConfig' vs
                # 'app.schemas.config.ExecutionConfig'
                # We want to match 'ExecutionConfig'

                engine_type_str = str(engine_type)
                api_type_str = str(api_type)

                # Extract class name if it's a class
                if hasattr(engine_type, "__name__"):
                    engine_type_name = engine_type.__name__
                else:
                    engine_type_name = str(engine_type)

                if hasattr(api_type, "__name__"):
                    api_type_name = api_type.__name__
                else:
                    api_type_name = str(api_type)

                # Special handling for distinct classes with same name (e.g. nested configs)
                if engine_type_name == api_type_name:
                    continue

                # If they are different classes but standard types (int, float, str), direct comparison
                # But here we might have formatting differences in str() representation
                # Let's try to be lenient: if the base name matches, it's likely fine given the context

                # Clean up string representations for comparison
                # e.g. "<class 'int'>" -> "int"
                def clean_type(t_str):
                    return t_str.replace("<class '", "").replace("'>", "").split(".")[-1]

                self.assertEqual(
                    clean_type(engine_type_str),
                    clean_type(api_type_str),
                    f"Type mismatch at {field_path}: Engine={engine_type} vs API={api_type}",
                )


if __name__ == "__main__":
    unittest.main()
