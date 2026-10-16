import uuid
from datetime import datetime
from sqlmodel import Column, Field, JSON, Session, SQLModel, create_engine, select
from pydantic import NaiveDatetime

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


class ConversationModel(SQLModel, table=True):
    __tablename__ = "conversation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    messages: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: NaiveDatetime = Field(default_factory=datetime.now)
    updated_at: NaiveDatetime = Field(default_factory=datetime.now)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        statement = select(ConversationModel)
        if not session.exec(statement).first():
            conversation = ConversationModel(messages=[])
            session.add(conversation)
            session.commit()


def get_session():
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
