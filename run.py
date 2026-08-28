# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Lancement du serveur Flask...")
    print("🌐 Accède à l'application sur : http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)