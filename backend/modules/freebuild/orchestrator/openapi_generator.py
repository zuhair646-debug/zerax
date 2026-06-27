"""
📋 OpenAPI Generator — auto-build OpenAPI 3.1 spec from a list of endpoints.

Input: list of endpoint dicts {method, path, summary, body_schema, response_schema}
Output: full OpenAPI YAML/JSON ready to serve via Swagger UI.

FastAPI generates this natively if you add tags + Pydantic models, so this
generator is mainly for explicit blueprints / customer-facing docs.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.openapi_gen")


def build_openapi_spec(
    title: str,
    version: str,
    endpoints: List[Dict[str, Any]],
    base_url: str = "/api",
    description: str = "",
) -> Dict[str, Any]:
    """Build a OpenAPI 3.1 spec dict.

    Each endpoint dict:
      - method: 'get' | 'post' | 'put' | 'delete'
      - path: '/users/{id}'
      - summary: short Arabic/English label
      - tags: ['users']
      - body_schema (optional): JSON schema for request body
      - response_schema (optional): JSON schema for 200 response
      - auth_required (optional, default True): bool
    """
    paths: Dict[str, Any] = {}
    schemas: Dict[str, Any] = {}

    for ep in endpoints:
        path = ep["path"]
        method = ep.get("method", "get").lower()
        op: Dict[str, Any] = {
            "summary": ep.get("summary", path),
            "tags": ep.get("tags", []),
            "operationId": ep.get("operation_id") or f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}",
            "responses": {
                "200": {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": ep.get("response_schema") or {"type": "object"}
                        }
                    }
                },
                "400": {"description": "Bad request"},
                "401": {"description": "Unauthorized"},
                "500": {"description": "Server error"}
            }
        }
        if ep.get("body_schema"):
            op["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": ep["body_schema"]}}
            }
        if ep.get("auth_required", True):
            op["security"] = [{"bearerAuth": []}]
        paths.setdefault(path, {})[method] = op

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "servers": [{"url": base_url}],
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        }
    }
    return spec


def render_swagger_html(spec_url: str = "/openapi.json", title: str = "API Docs") -> str:
    """Render a minimal Swagger UI HTML wrapper."""
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {{
      window.ui = SwaggerUIBundle({{
        url: "{spec_url}",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis],
      }});
    }};
  </script>
</body>
</html>"""


def endpoints_from_schema(db_schema: Dict[str, Any], base_path: str = "/api") -> List[Dict[str, Any]]:
    """Auto-generate REST endpoints from a DB schema (CRUD for each collection)."""
    out = []
    for coll in db_schema.get("collections_or_tables", []):
        name = coll["name"]
        sing = name.rstrip("s")
        # List
        out.append({
            "method": "get", "path": f"{base_path}/{name}", "tags": [name],
            "summary": f"List all {name}",
            "response_schema": {"type": "array", "items": {"type": "object"}},
        })
        # Create
        out.append({
            "method": "post", "path": f"{base_path}/{name}", "tags": [name],
            "summary": f"Create a {sing}",
            "body_schema": {"type": "object"},
            "response_schema": {"type": "object"},
        })
        # Get one
        out.append({
            "method": "get", "path": f"{base_path}/{name}/{{id}}", "tags": [name],
            "summary": f"Get a {sing}",
            "response_schema": {"type": "object"},
        })
        # Update
        out.append({
            "method": "put", "path": f"{base_path}/{name}/{{id}}", "tags": [name],
            "summary": f"Update a {sing}",
            "body_schema": {"type": "object"},
            "response_schema": {"type": "object"},
        })
        # Delete
        out.append({
            "method": "delete", "path": f"{base_path}/{name}/{{id}}", "tags": [name],
            "summary": f"Delete a {sing}",
            "response_schema": {"type": "object"},
        })
    return out
