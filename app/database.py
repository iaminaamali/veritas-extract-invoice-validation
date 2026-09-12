from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def create_tables() -> None:
    from app.models import Invoice  # noqa: F401

    Base.metadata.create_all(bind=engine)


def save_invoice(invoice, file_hash, status, confidence, attempts=0, validation_errors=None):
    from app.models import Invoice

    session = SessionLocal()
    try:
        db_invoice = Invoice(
            file_hash=file_hash,
            invoice_number=invoice.invoice_number,
            vendor_name=invoice.vendor_name,
            invoice_date=invoice.invoice_date,
            currency=invoice.currency.upper(),
            subtotal=invoice.subtotal,
            tax=invoice.tax,
            total=invoice.total,
            payment_terms=invoice.payment_terms,
            purchase_order_number=invoice.purchase_order_number,
            status=status,
            confidence=confidence,
            attempts=attempts,
            validation_errors="\n".join(validation_errors) if validation_errors else None,
        )
        session.add(db_invoice)
        session.commit()
        session.refresh(db_invoice)
        return db_invoice.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_invoice_by_hash(file_hash):
    from app.models import Invoice

    session = SessionLocal()
    try:
        return session.query(Invoice).filter(Invoice.file_hash == file_hash).first()
    finally:
        session.close()


def get_invoice_by_id(invoice_id):
    from app.models import Invoice

    session = SessionLocal()
    try:
        return session.query(Invoice).filter(Invoice.id == invoice_id).first()
    finally:
        session.close()


def approve_invoice_review(invoice_id):
    from app.models import Invoice

    session = SessionLocal()
    try:
        invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice is None:
            return None
        invoice.status = "VALIDATED"
        session.commit()
        session.refresh(invoice)
        return invoice
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
