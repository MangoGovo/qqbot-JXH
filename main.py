from ws.server import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, auto_reload=False, workers=7)
