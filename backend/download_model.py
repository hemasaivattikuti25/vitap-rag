from fastembed import TextEmbedding
import sys

def main():
    print("Pre-downloading FastEmbed model to local workspace cache...")
    try:
        model = TextEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_dir="./fastembed_cache"
        )
        print("Model pre-downloaded successfully to ./fastembed_cache!")
    except Exception as e:
        print(f"Error pre-downloading model: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
