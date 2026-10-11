from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine, select

from .adapter.gateway import ConversationModel

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

    # 建立一筆預設 Conversation
    with Session(engine) as session:
        # 若資料表為空則建立初始對話
        statement = select(ConversationModel)
        if not session.exec(statement).first():
            conversation = ConversationModel(
                messages=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
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
