from src.web.app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  منظومة إعمار ليبيا لنقل الركاب - Emaar Libya ERP")
    print("  http://localhost:5000")
    print("  admin / admin123")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
