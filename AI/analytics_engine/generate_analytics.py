import pandas as pd 
import numpy as np 
import re 
import json 
from sklearn.feature_extraction.text import TfidfVectorizer 
from sklearn.cluster import KMeans 
 
print("Starting analytics engine...") 
 
# Load the dataset 
try: 
    df = pd.read_csv('tickets.csv') 
    print(f"Successfully loaded {len(df)} tickets.") 
except FileNotFoundError: 
    print("Error: tickets.csv not found. Make sure it's in the same directory.") 
    exit() 
 
# --- Text Preprocessing --- 
# A simple function to clean the text data 
def preprocess_text(text): 
    if not isinstance(text, str): 
        return "" 
    # Remove punctuation 
    text = re.sub(r'[^\w\s]', '', text) 
    # Convert to lowercase 
    text = text.lower() 
    return text 
 
df['clean_description'] = df['description'].apply(preprocess_text) 

vectorizer = TfidfVectorizer(max_df=0.9, min_df=2, stop_words='english') 
X = vectorizer.fit_transform(df['clean_description']) 
print("Text data vectorized successfully.")

NUM_CLUSTERS = 5  
km = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10) 
km.fit(X) 
# Add the cluster ID to our original dataframe 
df['cluster'] = km.labels_ 
print(f"Clustering complete. Found {NUM_CLUSTERS} trends.") 


# --- Analyzing and Saving the Results --- 
clusters = [] 
# Get the feature names (the words) from the vectorizer 
terms = vectorizer.get_feature_names_out() 
 
# Get the centroids of the clusters 
order_centroids = km.cluster_centers_.argsort()[:, ::-1] 
 
for i in range(NUM_CLUSTERS): 
    cluster_size = int((df['cluster'] == i).sum()) 
     
    # Get the top 10 terms for this cluster 
    top_terms = [terms[ind] for ind in order_centroids[i, :10]] 
     
    cluster_info = { 
        "cluster_id": i, 
        "size": cluster_size, 
        "top_terms": top_terms, 
        "theme": f"Potential Theme: {top_terms[0]} & {top_terms[1]} issues" 
    } 
    clusters.append(cluster_info) 
 
# Create the final output dictionary 
output = { 
    "total_tickets": len(df), 
    "total_clusters": NUM_CLUSTERS, 
    "clusters": clusters 
} 
 
# Save to a JSON file 
with open('trends.json', 'w') as f: 
    json.dump(output, f, indent=4) 
 
print("Analytics complete. Output saved to trends.json") 


