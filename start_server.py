#! python
from src.ui.network_apis import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='9870', debug=True)
