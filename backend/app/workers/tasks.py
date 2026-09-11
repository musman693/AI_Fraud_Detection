"""
workers/tasks.py — Celery background tasks.
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.process_csv_import", max_retries=3)
def process_csv_import(self, job_id: str, csv_content_str: str, user_id: str) -> dict[str, Any]:
    """
    Process a CSV import job:
      1. Parse CSV rows
      2. Insert in batches of CSV_BATCH_SIZE
      3. Run detection pipeline per row (skip ML for bulk — use rule-only mode)
      4. Update CSVImportJob status

    Runs in a sync Celery worker but spins up its own asyncio event loop.
    """
    import pandas as pd, io

    # Lazy import here to avoid circular imports at module level
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    from app.core.config import settings as cfg
    from app.models.transaction import Transaction, CSVImportJob, ImportStatus
    from app.services.csv_import_service import row_to_create_request
    from app.core.security import encrypt_field

    # Use sync engine for Celery worker
    sync_engine = create_engine(cfg.DATABASE_SYNC_URL)
    SyncSession = sessionmaker(bind=sync_engine)

    with SyncSession() as db:
        job: CSVImportJob | None = db.get(CSVImportJob, job_id)
        if not job:
            logger.error("CSV import job %s not found", job_id)
            return {"error": "Job not found"}

        job.status = ImportStatus.PROCESSING
        db.commit()

        try:
            df = pd.read_csv(io.StringIO(csv_content_str), dtype=str, keep_default_na=False)
            total = len(df)
            job.total_rows = total
            db.commit()

            processed = 0
            failed = 0
            errors: list[str] = []

            for batch_start in range(0, total, cfg.CSV_BATCH_SIZE):
                batch = df.iloc[batch_start : batch_start + cfg.CSV_BATCH_SIZE]
                batch_txns: list[Transaction] = []

                for idx, row in batch.iterrows():
                    req = row_to_create_request(row.to_dict())
                    if req is None:
                        failed += 1
                        errors.append(f"Row {idx + 2}: parse error")
                        continue

                    # Encrypt PII
                    ip_enc = encrypt_field(req.ip_address) if req.ip_address else None
                    txn = Transaction(
                        customer_id=req.customer_id,
                        amount=req.amount,
                        currency=req.currency.upper(),
                        payment_method=req.payment_method,
                        transaction_datetime=req.transaction_datetime,
                        ip_address_enc=ip_enc,
                        account_age_days=req.account_age_days,
                        previous_transaction_count=req.previous_transaction_count,
                        merchant_id=req.merchant_id,
                        merchant_category=req.merchant_category,
                        source="csv_import",
                        created_by_user_id=user_id,
                        decision="pending",
                    )
                    batch_txns.append(txn)
                    processed += 1

                db.bulk_save_objects(batch_txns)
                db.commit()

                # Update progress
                job.processed_rows = processed
                job.failed_rows = failed
                db.commit()

                # Celery progress update
                self.update_state(
                    state="PROGRESS",
                    meta={"processed": processed, "failed": failed, "total": total},
                )

            job.status = ImportStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.error_log = json.dumps(errors[:100]) if errors else None  # cap log size
            db.commit()

            return {"processed": processed, "failed": failed, "total": total}

        except Exception as exc:
            logger.exception("CSV import task failed for job %s", job_id)
            job.status = ImportStatus.FAILED
            job.error_log = str(exc)
            db.commit()
            raise self.retry(exc=exc)
