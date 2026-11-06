"""主機管理命令；僅供持有主機存取權的部署者處理舊資料。"""
import argparse
import time

from sqlmodel import Session, select

from src.database import engine, init_db
from src.repositories.task_repo import TaskModel
from src.repositories.visitor_repo import VisitorModel


def list_legacy_tasks(session: Session) -> None:
    tasks = session.exec(select(TaskModel).where(TaskModel.owner_id.is_(None))).all()
    for task in tasks:
        print(f"{task.id}\t{task.name}")
    print(f"未指派任務：{len(tasks)}")


def assign_owner(session: Session, task_id: str, visitor_id: str) -> None:
    visitor = session.get(VisitorModel, visitor_id)
    if visitor is None or visitor.expires_at <= int(time.time()):
        raise SystemExit("訪客不存在或已到期，請先在目標瀏覽器開啟網站。")
    task = session.get(TaskModel, task_id)
    if task is None or task.owner_id is not None:
        raise SystemExit("只能指派尚未有擁有者的舊任務。")
    task.owner_id = visitor_id
    session.add(task)
    session.commit()
    print("舊任務已指派給指定訪客。")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("legacy-tasks")
    assign = commands.add_parser("assign-owner")
    assign.add_argument("--task-id", required=True)
    assign.add_argument("--visitor-id", required=True)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    init_db()
    with Session(engine) as session:
        if arguments.command == "legacy-tasks":
            list_legacy_tasks(session)
        else:
            assign_owner(session, arguments.task_id, arguments.visitor_id)


if __name__ == "__main__":
    main()
