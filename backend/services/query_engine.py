"""
Secure SQL-like Query Engine.
Parses a controlled SQL-like DSL and converts to safe Pandas operations.
NO eval(), NO exec(), NO OS commands.
"""
import re
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import structlog

logger = structlog.get_logger()

BLOCKED_KEYWORDS = [
    "exec", "eval", "import", "__", "os.", "sys.", "open(",
    "subprocess", "shutil", "glob", "pathlib", "builtins",
    "lambda", "compile", "getattr", "setattr", "delattr",
    "drop_duplicates", ".to_csv", ".to_excel", ".to_sql",
    "pickle", "marshal",
]

ALLOWED_AGGREGATIONS = {"sum", "mean", "count", "min", "max", "median", "std", "var"}


class QueryError(Exception):
    pass


def _sanitize_identifier(name: str) -> str:
    """Allow only alphanumeric + underscore column names."""
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_ ]*$', name.strip()):
        raise QueryError(f"Invalid identifier: '{name}'. Only alphanumeric and underscore allowed.")
    return name.strip()


def _check_blocked(query: str) -> None:
    """Reject queries containing blocked keywords."""
    lower = query.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in lower:
            raise QueryError(f"Blocked operation detected: '{kw}'")


# ──────────────────────────────────────────────
# TOKENIZER / PARSER
# ──────────────────────────────────────────────

def _parse_select_clause(clause: str) -> Tuple[List[str], Dict[str, str]]:
    """Parse SELECT columns. Supports: col1, SUM(col2) AS total"""
    columns = []
    agg_map: Dict[str, str] = {}  # alias -> "agg(col)"
    for part in clause.split(","):
        part = part.strip()
        # Match AGG(col) AS alias
        agg_match = re.match(
            r'(\w+)\(([^)]+)\)\s+(?:AS\s+)?(\w+)',
            part, re.IGNORECASE
        )
        if agg_match:
            agg_fn, col, alias = agg_match.groups()
            agg_fn = agg_fn.lower()
            if agg_fn not in ALLOWED_AGGREGATIONS:
                raise QueryError(f"Aggregation '{agg_fn}' not allowed. Allowed: {ALLOWED_AGGREGATIONS}")
            _sanitize_identifier(col)
            columns.append(alias)
            agg_map[alias] = (agg_fn, col.strip())
        else:
            # Plain column, possibly with alias
            as_match = re.match(r'(.+?)\s+(?:AS\s+)?(\w+)$', part, re.IGNORECASE)
            if as_match:
                col, alias = as_match.groups()
                _sanitize_identifier(col.strip())
                columns.append(alias)
                agg_map[alias] = ("rename", col.strip())
            else:
                _sanitize_identifier(part)
                columns.append(part)
    return columns, agg_map


def _apply_where(df: pd.DataFrame, where_clause: str) -> pd.DataFrame:
    """
    Apply WHERE conditions. Supports: col > val, col = 'str', col != val, AND, OR.
    """
    # Tokenize conditions
    conditions = re.split(r'\bAND\b|\band\b', where_clause)
    mask = pd.Series([True] * len(df), index=df.index)
    for cond in conditions:
        cond = cond.strip()
        # col OPERATOR value
        m = re.match(
            r"([A-Za-z_][A-Za-z0-9_ ]*)\s*(>=|<=|!=|=|>|<|LIKE|like)\s*(.+)",
            cond
        )
        if not m:
            raise QueryError(f"Cannot parse WHERE condition: '{cond}'")
        col, op, val_str = m.group(1).strip(), m.group(2).upper(), m.group(3).strip()
        _sanitize_identifier(col)
        if col not in df.columns:
            raise QueryError(f"Column '{col}' not found in dataset")
        # Parse value
        if val_str.startswith("'") and val_str.endswith("'"):
            val = val_str[1:-1]
        else:
            try:
                val = float(val_str)
            except ValueError:
                val = val_str

        if op == "=":
            mask &= df[col] == val
        elif op == ">":
            mask &= df[col] > val
        elif op == "<":
            mask &= df[col] < val
        elif op == ">=":
            mask &= df[col] >= val
        elif op == "<=":
            mask &= df[col] <= val
        elif op == "!=":
            mask &= df[col] != val
        elif op == "LIKE":
            pattern = val_str.strip("'").replace("%", ".*")
            mask &= df[col].astype(str).str.match(pattern, na=False)

    return df[mask]


# ──────────────────────────────────────────────
# MAIN QUERY EXECUTOR
# ──────────────────────────────────────────────

def execute_query(df: pd.DataFrame, query: str) -> Dict[str, Any]:
    """
    Parse and execute a controlled SQL-like query against a Pandas DataFrame.
    Query syntax: SELECT ... FROM data [WHERE ...] [GROUP BY ...] [ORDER BY ...] [LIMIT N]
    """
    if not query or not query.strip():
        raise QueryError("Empty query")
    if len(query) > 2000:
        raise QueryError("Query too long (max 2000 characters)")

    # Security pre-check
    _check_blocked(query)

    # Normalize whitespace
    q = " ".join(query.split())

    # Main regex parse
    pattern = re.compile(
        r'SELECT\s+(.+?)\s+FROM\s+\w+'
        r'(?:\s+WHERE\s+(.+?))?'
        r'(?:\s+GROUP\s+BY\s+(.+?))?'
        r'(?:\s+ORDER\s+BY\s+(.+?)(?:\s+(ASC|DESC))?)?'
        r'(?:\s+LIMIT\s+(\d+))?$',
        re.IGNORECASE | re.DOTALL
    )
    m = pattern.match(q)
    if not m:
        raise QueryError("Invalid query syntax. Expected: SELECT ... FROM data [WHERE ...] [GROUP BY ...] [ORDER BY ...] [LIMIT N]")

    select_clause = m.group(1)
    where_clause = m.group(2)
    group_by_clause = m.group(3)
    order_by_clause = m.group(4)
    order_dir = (m.group(5) or "ASC").upper()
    limit = int(m.group(6)) if m.group(6) else 1000

    result_df = df.copy()

    # WHERE
    if where_clause:
        result_df = _apply_where(result_df, where_clause)

    # Parse SELECT
    select_cols, agg_map = _parse_select_clause(select_clause)

    # GROUP BY + aggregations
    if group_by_clause:
        group_cols = [_sanitize_identifier(c) for c in group_by_clause.split(",")]
        for gc in group_cols:
            if gc not in result_df.columns:
                raise QueryError(f"GROUP BY column '{gc}' not found")

        agg_spec: Dict[str, Any] = {}
        for alias, mapping in agg_map.items():
            if mapping[0] == "rename":
                agg_spec[mapping[1]] = "first"
            else:
                agg_spec[mapping[1]] = mapping[0]

        if not agg_spec:
            raise QueryError("SELECT with GROUP BY must include at least one aggregation (SUM, COUNT, etc.)")

        result_df = result_df.groupby(group_cols).agg(agg_spec).reset_index()
        # Rename aggregated columns
        rename_map = {}
        for alias, mapping in agg_map.items():
            if mapping[0] != "rename":
                rename_map[mapping[1]] = alias
        result_df = result_df.rename(columns=rename_map)

    else:
        # No GROUP BY – just select columns
        plain_cols = []
        for alias in select_cols:
            if alias in agg_map and agg_map[alias][0] == "rename":
                orig = agg_map[alias][1]
                if orig in result_df.columns:
                    result_df = result_df.rename(columns={orig: alias})
                    plain_cols.append(alias)
            elif alias in result_df.columns:
                plain_cols.append(alias)
            elif alias == "*":
                plain_cols = list(result_df.columns)
                break
        if plain_cols:
            result_df = result_df[plain_cols]

    # ORDER BY
    if order_by_clause:
        order_col = _sanitize_identifier(order_by_clause.split(",")[0])
        if order_col in result_df.columns:
            result_df = result_df.sort_values(order_col, ascending=(order_dir == "ASC"))

    # LIMIT
    result_df = result_df.head(min(limit, 5000))

    # Serialize result
    columns = list(result_df.columns)
    rows = result_df.where(result_df.notna(), None).values.tolist()

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }
