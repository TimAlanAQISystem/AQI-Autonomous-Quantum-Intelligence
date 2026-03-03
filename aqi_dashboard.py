from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "service": "AQI Agent X dashboard (stub)"}

@app.get("/health")
def health():
    return {"healthy": True}
