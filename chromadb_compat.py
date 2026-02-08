"""
ChromaDB Python 3.14 Compatibility Patch

This module patches the Pydantic v1 compatibility issues with Python 3.14
that prevent ChromaDB from loading.
"""

import sys

# Monkey-patch before importing chromadb
def patch_pydantic():
    """Patch Pydantic v1 to work with Python 3.14."""
    try:
        import pydantic.v1.fields as fields
        original_set_default_and_type = fields.ModelField._set_default_and_type

        def patched_set_default_and_type(self):
            """Patched version that provides default types for problematic fields."""
            try:
                return original_set_default_and_type(self)
            except Exception as e:
                # If type inference fails, provide a default
                if "unable to infer type" in str(e):
                    # Set a reasonable default type (Any or int for server params)
                    from typing import Any, Optional
                    if self.name in ['chroma_server_nofile', 'chroma_server_timeout']:
                        self.type_ = Optional[int]
                        self.outer_type_ = Optional[int]
                    else:
                        self.type_ = Any
                        self.outer_type_ = Any
                    return
                raise

        fields.ModelField._set_default_and_type = patched_set_default_and_type

    except Exception as e:
        print(f"Warning: Could not apply Pydantic patch: {e}", file=sys.stderr)


# Apply patch immediately
patch_pydantic()
