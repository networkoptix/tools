import json
from fastapi import FastAPI, Request
from pathlib import Path
from tempfile import gettempdir

help = '''
Mock utility for emulating cloud layouts storage.
Requires Python 3.10+, fastapi and uvicorn python modules.

Run: uvicorn cloud_layouts_mock:app --reload
Will listen on the localhost:8000 by default.
'''

app = FastAPI()

storage = Path(gettempdir()) / 'cloud_layouts'


@app.get("/docdb/v1/docs/{file_path:path}")
async def get_layout(file_path: str, matchPrefix: str | None = None):
    if matchPrefix is not None:
        result = []
        for file in storage.glob(f"{matchPrefix}**/*.*"):
            with open(file, "r") as data:
                result.append(json.load(data))
        return result

    full_path = storage / file_path
    if full_path.exists():
        with open(full_path, "r") as data:
            return json.load(data)

    return {
        "message": f"{file_path} is not found"
    }


@app.post("/docdb/v1/docs/{file_path:path}")
async def save_layout(file_path: str, request: Request):
    data = await request.json()
    full_path = storage / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w") as file:
        json.dump(data, file)
    return {"message": f"File saved to {full_path}"}


@app.delete("/docdb/v1/docs/{file_path:path}")
async def delete_layout(file_path: str, request: Request):
    full_path = storage / file_path
    full_path.unlink()
    return {"message": f"File {full_path} deleted"}


if __name__ == "__main__":
    print(help)
