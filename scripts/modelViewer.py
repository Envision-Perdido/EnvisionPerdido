import joblib

model_path = '/Users/jacob/Desktop/EnvisionPerdido/data/artifacts/event_classifier_model.pkl'
vectorizer_path = '/Users/jacob/Desktop/EnvisionPerdido/data/artifacts/event_vectorizer.pkl'

try:
    model = joblib.load(model_path)
    vectorizer = joblib.load(vectorizer_path)
    print("Model and vectorizer loaded successfully\n")
    print("Model details:")
    print(model)
    print("\nVectorizer details:")
    print(vectorizer)

    # Example: Predict on new data
    example_texts = [
        "Sample event description about a community cleanup.",
        "Join us for a music festival downtown!"
    ]
    X = vectorizer.transform(example_texts)
    predictions = model.predict(X)
    print("\nPredictions for example texts:")
    for text, pred in zip(example_texts, predictions):
        print(f"Text: {text}\nPredicted label: {pred}\n")
except FileNotFoundError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"An error occurred while loading the model or vectorizer: {e}")