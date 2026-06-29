import json
import logging
from sqlalchemy import select, insert, update, delete
from core.db.engine import get_session, generated_tables

logger = logging.getLogger(__name__)

def row_to_dict(row):
    return dict(row._mapping) if row else None

def rows_to_dict_list(rows):
    return [dict(row._mapping) for row in rows]

class DBManager:
    def _get_table(self, schema_class):
        tablename = getattr(schema_class, '__tablename__', schema_class.__name__.lower())
        table = generated_tables.get(tablename)
        if table is None:
            raise ValueError(f"Table '{tablename}' not found in registry.")
        return table

    def get(self, schema_class, **kwargs) -> dict:
        table = self._get_table(schema_class)
        with next(get_session()) as session:
            stmt = select(table)
            for k, v in kwargs.items():
                stmt = stmt.where(getattr(table.c, k) == v)
            return row_to_dict(session.execute(stmt).fetchone())

    def filter(self, schema_class, order_by=None, descending=False, **kwargs) -> list:
        table = self._get_table(schema_class)
        with next(get_session()) as session:
            stmt = select(table)
            for k, v in kwargs.items():
                if v is None:
                    stmt = stmt.where(getattr(table.c, k).is_(None))
                else:
                    stmt = stmt.where(getattr(table.c, k) == v)
            if order_by:
                col = getattr(table.c, order_by)
                stmt = stmt.order_by(col.desc() if descending else col.asc())
            return rows_to_dict_list(session.execute(stmt).fetchall())

    def create(self, schema_class, **kwargs):
        table = self._get_table(schema_class)
        with next(get_session()) as session:
            stmt = insert(table).values(**kwargs)
            res = session.execute(stmt)
            session.commit()
            return res.inserted_primary_key[0] if res.inserted_primary_key else None

    def update(self, schema_class, filters: dict, updates: dict):
        table = self._get_table(schema_class)
        with next(get_session()) as session:
            stmt = update(table)
            for k, v in filters.items():
                if v is None:
                    stmt = stmt.where(getattr(table.c, k).is_(None))
                else:
                    stmt = stmt.where(getattr(table.c, k) == v)
            stmt = stmt.values(**updates)
            session.execute(stmt)
            session.commit()

    def delete(self, schema_class, **kwargs):
        table = self._get_table(schema_class)
        with next(get_session()) as session:
            stmt = delete(table)
            for k, v in kwargs.items():
                if v is None:
                    stmt = stmt.where(getattr(table.c, k).is_(None))
                else:
                    stmt = stmt.where(getattr(table.c, k) == v)
            session.execute(stmt)
            session.commit()

    def get_session(self):
        return get_session()

    def get_table(self, schema_class):
        return self._get_table(schema_class)

# Initialize DB on load
from core.db.engine import init_db
init_db()

db = DBManager()
