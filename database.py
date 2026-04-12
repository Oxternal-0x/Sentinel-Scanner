import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


class SentinelDB:
    def __init__(self, db_path: str = "sentinel_vault.db"):
        self.db_path = db_path
        self._bootstrap()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _bootstrap(self) -> None:
        """Initializes and incrementally migrates the database schema."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    protocol TEXT NOT NULL,
                    chain TEXT NOT NULL,
                    address TEXT,
                    tvl REAL,
                    score INTEGER,
                    risk_level TEXT,
                    source_quality TEXT,
                    jurisdiction TEXT,
                    result_json TEXT,
                    manifest_version TEXT,
                    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS manifests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    source_title TEXT,
                    jurisdiction TEXT,
                    manifest_json TEXT NOT NULL,
                    diff_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS social_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    protocol TEXT NOT NULL,
                    source TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL DEFAULT 0,
                    summary TEXT NOT NULL,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS badge_eligibility (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    protocol TEXT NOT NULL,
                    chain TEXT NOT NULL,
                    address TEXT,
                    score INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    metadata_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            self._ensure_column(conn, "audits", "address", "TEXT")
            self._ensure_column(conn, "audits", "source_quality", "TEXT")
            self._ensure_column(conn, "audits", "jurisdiction", "TEXT")
            self._ensure_column(conn, "audits", "manifest_version", "TEXT")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_protocol ON audits(protocol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_risk ON audits(risk_level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_manifest_version ON manifests(version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_social_protocol ON social_signals(protocol)")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def save_audit(
        self,
        protocol: str,
        chain: str,
        tvl: float,
        score: int,
        result: Dict,
        address: Optional[str] = None,
        source_quality: str = "unknown",
        jurisdiction: str = "global",
        manifest_version: Optional[str] = None,
    ) -> None:
        """Persists a new audit record."""
        risk = "HIGH" if score < 50 else "MEDIUM" if score < 80 else "LOW"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audits (
                    protocol, chain, address, tvl, score, risk_level,
                    source_quality, jurisdiction, result_json, manifest_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    protocol,
                    chain,
                    address,
                    tvl,
                    score,
                    risk,
                    source_quality,
                    jurisdiction,
                    json.dumps(result),
                    manifest_version,
                ),
            )

        print(f"📁 Audit persisted to Ledger: {protocol} ({risk})")

    def save_manifest_snapshot(
        self,
        version: str,
        source_title: str,
        jurisdiction: str,
        manifest: Dict,
        diff: Optional[Dict] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO manifests (version, source_title, jurisdiction, manifest_json, diff_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    version,
                    source_title,
                    jurisdiction,
                    json.dumps(manifest),
                    json.dumps(diff or {}),
                ),
            )

    def save_social_signal(
        self,
        protocol: str,
        source: str,
        signal_type: str,
        summary: str,
        confidence: float = 0.0,
        raw_payload: Optional[Dict] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO social_signals (protocol, source, signal_type, confidence, summary, raw_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    protocol,
                    source,
                    signal_type,
                    confidence,
                    summary,
                    json.dumps(raw_payload or {}),
                ),
            )

    def save_badge_eligibility(
        self,
        protocol: str,
        chain: str,
        address: Optional[str],
        score: int,
        status: str,
        metadata_path: Optional[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO badge_eligibility (protocol, chain, address, score, status, metadata_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (protocol, chain, address, score, status, metadata_path),
            )

    def get_latest_manifest(self) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT version, source_title, jurisdiction, manifest_json, diff_json, created_at
                FROM manifests
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if not row:
            return None

        return {
            "version": row["version"],
            "source_title": row["source_title"],
            "jurisdiction": row["jurisdiction"],
            "manifest": json.loads(row["manifest_json"]),
            "diff": json.loads(row["diff_json"] or "{}"),
            "created_at": row["created_at"],
        }

    def get_latest_audit(self, protocol_name: str) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT protocol, chain, address, tvl, score, risk_level, source_quality,
                       jurisdiction, result_json, manifest_version, run_at
                FROM audits
                WHERE protocol = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (protocol_name,),
            ).fetchone()

        if not row:
            return None

        result = dict(row)
        result["result"] = json.loads(result.pop("result_json"))
        return result

    def get_history(self, protocol_name: Optional[str] = None, limit: int = 10) -> List[sqlite3.Row]:
        query = """
            SELECT protocol, score, risk_level, run_at, chain, source_quality
            FROM audits
        """
        params: List[object] = []
        if protocol_name:
            query += " WHERE protocol = ?"
            params.append(protocol_name)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def get_heatmap_data(self, limit: int = 100) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT protocol, chain, tvl, score, risk_level, source_quality, run_at
                FROM audits
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_recent_social_signals(self, protocol: Optional[str] = None, limit: int = 20) -> List[Dict]:
        query = """
            SELECT protocol, source, signal_type, confidence, summary, created_at
            FROM social_signals
        """
        params: List[object] = []
        if protocol:
            query += " WHERE protocol = ?"
            params.append(protocol)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_protocols_newly_at_risk(self, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT current.protocol, current.chain, current.score, current.risk_level, current.run_at
                FROM audits AS current
                JOIN (
                    SELECT protocol, MAX(id) AS latest_id
                    FROM audits
                    GROUP BY protocol
                ) AS latest ON latest.latest_id = current.id
                WHERE current.risk_level IN ('HIGH', 'MEDIUM')
                ORDER BY current.score ASC, current.run_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM audits").fetchone()["count"]
            high_risk = conn.execute(
                "SELECT COUNT(*) AS count FROM audits WHERE risk_level = 'HIGH'"
            ).fetchone()["count"]
            medium_risk = conn.execute(
                "SELECT COUNT(*) AS count FROM audits WHERE risk_level = 'MEDIUM'"
            ).fetchone()["count"]
            low_risk = conn.execute(
                "SELECT COUNT(*) AS count FROM audits WHERE risk_level = 'LOW'"
            ).fetchone()["count"]

        return {
            "total": total,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
        }

    def get_latest_high_risk(self) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT protocol, chain, address, tvl, score, risk_level, run_at, result_json
                FROM audits
                WHERE risk_level IN ('HIGH', 'MEDIUM')
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if not row:
            return None

        result = dict(row)
        result["result"] = json.loads(result.pop("result_json"))
        return result

    @staticmethod
    def new_manifest_version() -> str:
        return datetime.utcnow().strftime("%Y%m%d%H%M%S")
