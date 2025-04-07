from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/")
async def webhook_listener(request: Request):
    data = await request.json()
    print("###>>>>>>>>>> Webhook received..........:", data)
    return {"message": "Received Successfully..........."}
