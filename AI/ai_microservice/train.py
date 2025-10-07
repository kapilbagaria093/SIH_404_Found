import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import joblib
import os

print("Starting model training...")

# Create model_artifacts directory if it doesn't exist
os.makedirs('model_artifacts', exist_ok=True)

try:
    # 1. Load Data with error checking
    print("Loading training data...")
    df = pd.read_csv('tickets_for_training.csv').dropna()
    
    # Check if required columns exist
    if 'category' not in df.columns:
        print("❌ Error: 'category' column not found in CSV")
        print(f"Available columns: {df.columns.tolist()}")
        exit()
    
    if 'description' not in df.columns:
        print("❌ Error: 'description' column not found in CSV")
        print(f"Available columns: {df.columns.tolist()}")
        exit()
    
    print(f"✅ Loaded {len(df)} training examples")
    print(f"Categories: {df['category'].unique()}")

    # 2. Encode Labels
    le = LabelEncoder()
    df['category_encoded'] = le.fit_transform(df['category'])

    # 3. Split Data
    X = df['description']
    y = df['category_encoded']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. Create an ML Pipeline
    model_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_df=0.95, min_df=2, stop_words='english')),
        ('clf', LinearSVC(C=1.0, random_state=42))
    ])

    # 5. Train the Model
    print("Training the classification model...")
    model_pipeline.fit(X_train, y_train)

    # 6. Evaluate
    accuracy = model_pipeline.score(X_test, y_test)
    print(f"✅ Model accuracy on test set: {accuracy:.2f}")

    # 7. Save the Model and the Label Encoder
    print("Saving model artifacts...")
    joblib.dump(model_pipeline, 'model_artifacts/ticket_classifier.pkl')
    joblib.dump(le, 'model_artifacts/label_encoder.pkl')
    print("✅ Training complete. Model saved in 'model_artifacts/'.")

except Exception as e:
    print(f"❌ Training failed: {e}")
