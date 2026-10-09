import os
from dotenv import load_dotenv
load_dotenv()
from dataclasses import dataclass, field

import datasets
import duckdb
import pandas as pd

from pydantic_ai import Agent, ModelRetry, RunContext


@dataclass
class AnalystAgentDeps:
    output: dict[str, pd.DataFrame] = field(default_factory=dict[str, pd.DataFrame])

    def store(self, value: pd.DataFrame) -> str:
        """儲存分析結果並回傳一個變數名稱，如Out[1]，讓LLM可以繼續使用此變數"""
        ref = f"Out[{len(self.output) + 1}]"
        self.output[ref] = value
        return ref

    def get(self, ref: str) -> pd.DataFrame:
        if ref not in self.output:
            raise ModelRetry(
                f"錯誤：{ref}不是一個有效的變數名稱。請檢查之前的訊息並重試。"
            )
        return self.output[ref]


model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
analyst_agent = Agent(
    model,
    deps_type=AnalystAgentDeps,
    instructions="你是資料分析師，你的工作是根據使用者需求分析資料。",
)


@analyst_agent.tool
def load_dataset(
    ctx: RunContext[AnalystAgentDeps],
    path: str,
    split: str = "train",
) -> str:
    """載入 huggingface 的資料集，並將結果儲存起來。

    Args:
        ctx: Pydantic AI agent RunContext
        path: 資料集的名稱，格式為 `<user_name>/<dataset_name>`
        split: 資料集的分支，預設為 "train"
    """
    # begin load data from hf
    builder = datasets.load_dataset_builder(path)  # pyright: ignore[reportUnknownMemberType]
    splits: dict[str, datasets.SplitInfo] = builder.info.splits or {}
    if split not in splits:
        raise ModelRetry(
            f"{split} is not valid for dataset {path}. Valid splits are {','.join(splits.keys())}"
        )

    builder.download_and_prepare()  # pyright: ignore[reportUnknownMemberType]
    dataset = builder.as_dataset(split=split)
    assert isinstance(dataset, datasets.Dataset)
    dataframe = dataset.to_pandas()
    assert isinstance(dataframe, pd.DataFrame)
    # end load data from hf

    # store the dataframe in the deps and get a ref like "Out[1]"
    ref = ctx.deps.store(dataframe)
    # construct a summary of the loaded dataset
    output = [
        f"Loaded the dataset as `{ref}`.",
        f"Description: {dataset.info.description}"
        if dataset.info.description
        else None,
        f"Features: {dataset.info.features!r}" if dataset.info.features else None,
    ]
    return "\n".join(filter(None, output))


@analyst_agent.tool
def run_duckdb(ctx: RunContext[AnalystAgentDeps], dataset: str, sql: str) -> str:
    """在 DataFrame 上執行 DuckDB SQL 查詢。

    注意：在 DuckDB SQL 中使用的虛擬表格名稱必須是 `dataset`。

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: DataFrame 的參考字串
        sql: 要用 DuckDB 執行的查詢
    """
    data = ctx.deps.get(dataset)
    result = duckdb.query_df(df=data, virtual_table_name="dataset", sql_query=sql)
    # pass the result as ref (because DuckDB SQL can select many rows, creating another huge dataframe)
    ref = ctx.deps.store(result.df())
    return f"執行 SQL 完畢，結果儲存於 `{ref}`"


@analyst_agent.tool
def display(ctx: RunContext[AnalystAgentDeps], name: str) -> str:
    """顯示 DataFrame 的前 5 列"""
    dataset = ctx.deps.get(name)
    return dataset.head().to_string()  # pyright: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    deps = AnalystAgentDeps()
    result = analyst_agent.run_sync(
        user_prompt="計算資料集 `cornell-movie-review-data/rotten_tomatoes` 中有多少負面評論",
        deps=deps,
    )
    print(result.output)
