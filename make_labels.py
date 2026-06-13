import os
import time
from typing import List, Literal

import pandas as pd
from google import genai
from pydantic import BaseModel, Field

client = genai.Client()


class ClassificationResponse(BaseModel):
    categories: List[Literal["A", "N", "G", "C"]] = Field(
        description="List of classified categories for the problems, matching the input list size and order."
    )


INPUT_PATH = "/home/yauheni/pet_projects/GeoSemantics/data/train-00000-of-00001.parquet"
OUTPUT_PATH = "/home/yauheni/pet_projects/GeoSemantics/data/train_classified.parquet"

if os.path.exists(OUTPUT_PATH):
    print("Обнаружен файл с прогрессом. Загружаем...")
    df = pd.read_parquet(OUTPUT_PATH)
else:
    print("Файл прогресса не найден. Начинаем обработку с нуля...")
    df = pd.read_parquet(INPUT_PATH)
    df = df[["problem"]].copy()
    df["type"] = None

to_classify = df[df["type"].isna()]
problems_len = len(to_classify)

print(f"Всего задач в базе: {len(df)}")
print(f"Осталось классифицировать: {problems_len}")

BATCH_SIZE = 50
DELAY_BETWEEN_REQUESTS = 4.0

system_instruction = (
    "You are an expert mathematical classifier. Your task is to classify "
    "mathematical olympiad problems into one of four categories:\n"
    "- 'A' for Algebra\n"
    "- 'N' for Number Theory\n"
    "- 'G' for Geometry\n"
    "- 'C' for Combinatorics\n\n"
    "You will receive a numbered list of problems. You must analyze each problem "
    "and return the classification labels in the exact same order as the input list."
)

if problems_len > 0:
    for first_ind in range(0, problems_len, BATCH_SIZE):
        batch = to_classify.iloc[first_ind : first_ind + BATCH_SIZE]

        prompt = ""
        for index, row in batch.iterrows():
            prompt += f"Problem {index}: {row['problem']}\n\n"

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=dict(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ClassificationResponse,
                    temperature=1,
                ),  # type: ignore
            )

            result: ClassificationResponse = response.parsed  # type: ignore

            if result and result.categories:
                categories = result.categories
                if len(categories) == len(batch):
                    df.loc[batch.index, "type"] = categories

                    df.to_parquet(OUTPUT_PATH)
                    print(
                        f"Успешно обработан батч {first_ind // BATCH_SIZE + 1}. "
                        f"Прогресс сохранён в {OUTPUT_PATH}"
                    )
                else:
                    print(
                        f"Предупреждение для батча с индекса {first_ind}: "
                        f"модель вернула {len(categories)} ответов вместо {len(batch)}. Пропускаем."
                    )
            else:
                print(
                    f"Ошибка: Не удалось распарсить ответ для батча с индекса {first_ind}"
                )

        except Exception as e:
            print(f"Ошибка при обработке батча с индекса {first_ind}: {e}")
            print("Прерываем выполнение, чтобы сохранить текущий прогресс.")
            break

        time.sleep(DELAY_BETWEEN_REQUESTS)
else:
    print("Все задачи уже классифицированы.")

unclassified_count = df["type"].isna().sum()
print(f"Обработка завершена. Неразмеченных задач осталось: {unclassified_count}")
