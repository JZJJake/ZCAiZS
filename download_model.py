import os

# Use HuggingFace mirror for users in mainland China
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from sentence_transformers import SentenceTransformer

def download_model():
    model_name = "shibing624/text2vec-base-chinese"
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "text2vec-base-chinese")

    if os.path.exists(save_path) and os.listdir(save_path):
        print(f"Model already exists at {save_path}. Skipping download.")
        return

    print(f"Downloading model {model_name} to {save_path} using mirror https://hf-mirror.com ...")
    try:
        # Load model from huggingface mirror
        model = SentenceTransformer(model_name)
        # Save model locally
        model.save(save_path)
        print("Model downloaded and saved successfully. You can now use it offline.")
    except Exception as e:
        print(f"Error downloading model: {e}")
        print("Please ensure you have internet access to download the model for the first time.")

if __name__ == "__main__":
    download_model()
