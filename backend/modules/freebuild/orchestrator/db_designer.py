"""
🗃️ Database Designer Cortex — real schema design (Mongo or Postgres).

Input: domain brief (e.g. "متجر عطور مع منتجات وطلبات وعملاء")
Output: structured schema with collections/tables + indexes + relations.

Uses LLM (Claude) for the design + validation.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.db_designer")


_DB_DESIGN_PROMPT = """أنت Database Architect مع 10 سنين خبرة Mongo + Postgres.

من brief العميل، صمّم schema حقيقي. أرجع JSON صرف:

{
  "database_type": "mongodb | postgres",
  "rationale": "لماذا اخترت هذا (3 أسطر)",
  "collections_or_tables": [
    {
      "name": "users",
      "fields": [
        {"name": "id", "type": "uuid", "required": true, "primary": true},
        {"name": "email", "type": "string", "required": true, "unique": true, "indexed": true},
        {"name": "created_at", "type": "datetime", "required": true, "default": "now()"}
      ],
      "indexes": [
        {"name": "email_idx", "fields": ["email"], "unique": true}
      ]
    }
  ],
  "relationships": [
    {"from": "orders.user_id", "to": "users.id", "type": "many-to-one"}
  ],
  "erd_mermaid": "erDiagram\\n  USERS ||--o{ ORDERS : places",
  "sample_aggregations": [
    {"name": "monthly_revenue", "pipeline_or_sql": "..."}
  ]
}

**القواعد:**
- اختر Mongo للـ document-heavy, varied schemas, real-time apps.
- اختر Postgres للـ transactions, relations, financial data.
- كل collection/table له id + created_at + updated_at.
- استخدم UUID لـ id (مش auto-increment).
- index على كل field يُستخدم في WHERE/lookup.
- لا تشرح، JSON صرف."""


async def design_database(brief: str, brand_dna: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        ctx = brief[:1000]
        if brand_dna and brand_dna.get("category"):
            ctx += f"\n\nCategory: {brand_dna['category']}"
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"db_design_{uuid.uuid4().hex[:8]}",
            system_message=_DB_DESIGN_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=ctx))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception as e:
                logger.warning(f"[db_designer] JSON parse: {e}")
    except Exception as e:
        logger.warning(f"[db_designer] LLM call failed: {e}")
    return None


def render_schema_as_mongo_pydantic(schema: Dict[str, Any]) -> str:
    """Render schema as Python Pydantic models for Mongo."""
    if not schema or schema.get("database_type") != "mongodb":
        return ""
    lines = ["from datetime import datetime", "from typing import Optional, List", "from pydantic import BaseModel, Field", "import uuid", ""]
    for coll in schema.get("collections_or_tables", []):
        name = coll["name"].capitalize().rstrip("s")
        lines.append(f"class {name}(BaseModel):")
        for field in coll.get("fields", []):
            fname = field["name"]
            ftype = _mongo_type(field["type"])
            default = "" if field.get("required") else " = None"
            if field.get("default"):
                if field["default"] == "now()":
                    default = " = Field(default_factory=lambda: datetime.utcnow())"
                else:
                    default = f" = {field['default']!r}"
            type_str = ftype if field.get("required") else f"Optional[{ftype}]"
            lines.append(f"    {fname}: {type_str}{default}")
        lines.append("")
    return "\n".join(lines)


def render_schema_as_postgres_sql(schema: Dict[str, Any]) -> str:
    """Render schema as PostgreSQL CREATE TABLE statements."""
    if not schema or schema.get("database_type") != "postgres":
        return ""
    out = []
    for tbl in schema.get("collections_or_tables", []):
        cols = []
        for field in tbl.get("fields", []):
            line = f"  {field['name']} {_pg_type(field['type'])}"
            if field.get("primary"): line += " PRIMARY KEY"
            if field.get("unique"): line += " UNIQUE"
            if field.get("required"): line += " NOT NULL"
            if field.get("default") == "now()": line += " DEFAULT now()"
            cols.append(line)
        out.append(f"CREATE TABLE {tbl['name']} (\n" + ",\n".join(cols) + "\n);")
        for idx in tbl.get("indexes", []):
            unique = "UNIQUE " if idx.get("unique") else ""
            cols_s = ", ".join(idx["fields"])
            out.append(f"CREATE {unique}INDEX {idx['name']} ON {tbl['name']} ({cols_s});")
    return "\n\n".join(out)


def _mongo_type(t: str) -> str:
    return {"uuid": "str", "string": "str", "int": "int", "float": "float",
            "bool": "bool", "datetime": "datetime", "list": "List", "dict": "dict"}.get(t.lower(), "str")


def _pg_type(t: str) -> str:
    return {"uuid": "UUID", "string": "TEXT", "int": "INTEGER", "float": "REAL",
            "bool": "BOOLEAN", "datetime": "TIMESTAMPTZ", "list": "JSONB", "dict": "JSONB"}.get(t.lower(), "TEXT")
