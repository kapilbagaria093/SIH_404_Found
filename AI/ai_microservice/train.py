import pandas as pd
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import joblib

print("Starting model training...")

# --- 1. Load Bootstrap Data ---
print("Loading data from tickets_for_training.csv...")
df_csv = pd.read_csv("tickets_for_training.csv")

# --- 2. Load Live Data from Database (Safely) ---
try:
    print("Attempting to load data from the database...")
    # IMPORTANT: Replace with your actual password and database name
    DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost/powergrid_helpdesk"
    engine = create_engine(DATABASE_URL)
    query = "SELECT description, category FROM tickets WHERE status = 'Resolved';"
    df_db = pd.read_sql(query, engine)
    print(f"Successfully loaded {len(df_db)} records from the database.")
except Exception as e:
    print(f"Could not connect to the database. Training on CSV data only. Error: {e}")
    df_db = pd.DataFrame() # Create an empty DataFrame if connection fails

# --- 3. Combine Datasets ---
# This combines the bootstrap CSV data with the new data from the database
training_df = pd.concat([df_csv, df_db], ignore_index=True)
print(f"Total training records: {len(training_df)}")

# --- 4. Prepare Data for Training ---
# Drop any rows with missing descriptions or categories
training_df.dropna(subset=['description', 'category'], inplace=True)

# Encode text labels (e.g., "Hardware") into numbers (e.g., 0)
le = LabelEncoder()
training_df['category_encoded'] = le.fit_transform(training_df['category'])

# Split the combined data into training and testing sets
X = training_df['description']
y = training_df['category_encoded']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# --- 5. Define and Train the ML Pipeline ---
model_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_df=0.95, min_df=2, stop_words='english')),
    ('clf', LinearSVC(C=1.0, random_state=42))
])

print("Training the classification model...")
model_pipeline.fit(X_train, y_train)

# --- 6. Evaluate and Save ---
accuracy = model_pipeline.score(X_test, y_test)
print(f"Model accuracy on test set: {accuracy:.2f}")

print("Saving model artifacts...")
joblib.dump(model_pipeline, 'model_artifacts/ticket_classifier.pkl')
joblib.dump(le, 'model_artifacts/label_encoder.pkl')

print("Training complete. Model and label encoder saved in 'model_artifacts/'.")