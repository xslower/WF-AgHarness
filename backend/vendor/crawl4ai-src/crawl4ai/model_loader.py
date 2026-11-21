from functools import lru_cache
from pathlib import Path
import subprocess, os
import shutil
from .model_loader import *
import argparse
from crawl4ai.config import MODEL_REPO_BRANCH

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


@lru_cache()
def get_available_memory(device):
    import torch

    if device.type == "cuda":
        return torch.cuda.get_device_properties(device).total_memory
    elif device.type == "mps":
        return 48 * 1024**3
    else:
        return 0


@lru_cache()
def calculate_batch_size(device):
    available_memory = get_available_memory(device)

    if device.type == "cpu":
        return 16
    elif device.type in ["cuda", "mps"]:
        pass
        if available_memory >= 31 * 1024**3:
            return 256
        elif available_memory >= 15 * 1024**3:
            return 128
        elif available_memory >= 8 * 1024**3:
            return 64
        else:
            return 32
    else:
        return 16


@lru_cache()
def get_device():
    import torch

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    return device


def set_model_device(model):
    device = get_device()
    model.to(device)
    return model, device


@lru_cache()
def get_home_folder():
    home_folder = os.path.join(
        os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home()), ".crawl4ai"
    )
    os.makedirs(home_folder, exist_ok=True)
    os.makedirs(f"{home_folder}/cache", exist_ok=True)
    os.makedirs(f"{home_folder}/models", exist_ok=True)
    return home_folder


@lru_cache()
def load_bert_base_uncased():
    from transformers import BertTokenizer, BertModel

    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", resume_download=None)
    model = BertModel.from_pretrained("bert-base-uncased", resume_download=None)
    model.eval()
    model, device = set_model_device(model)
    return tokenizer, model


@lru_cache()
def load_HF_embedding_model(model_name="BAAI/bge-small-en-v1.5") -> tuple:
    from transformers import AutoTokenizer, AutoModel

    tokenizer = AutoTokenizer.from_pretrained(model_name, resume_download=None)
    model = AutoModel.from_pretrained(model_name, resume_download=None)
    model.eval()
    model, device = set_model_device(model)
    return tokenizer, model


@lru_cache()
def load_text_classifier():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from transformers import pipeline

    tokenizer = AutoTokenizer.from_pretrained(
        "dstefa/roberta-base_topic_classification_nyt_news"
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        "dstefa/roberta-base_topic_classification_nyt_news"
    )
    model.eval()
    model, device = set_model_device(model)
    pipe = pipeline("text-classification", model=model, tokenizer=tokenizer)
    return pipe


@lru_cache()
def load_text_multilabel_classifier():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from scipy.special import expit
    import torch

    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass

    MODEL = "cardiffnlp/tweet-topic-21-multi"
    tokenizer = AutoTokenizer.from_pretrained(MODEL, resume_download=None)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, resume_download=None
    )
    model.eval()
    model, device = set_model_device(model)
    class_mapping = model.config.id2label

    def _classifier(texts, threshold=0.5, max_length=64):
        tokens = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        tokens = {
            key: val.to(device) for key, val in tokens.items()
        }

        with torch.no_grad():
            output = model(**tokens)

        scores = output.logits.detach().cpu().numpy()
        scores = expit(scores)
        predictions = (scores >= threshold) * 1

        batch_labels = []
        for prediction in predictions:
            labels = [
                class_mapping[i] for i, value in enumerate(prediction) if value == 1
            ]
            batch_labels.append(labels)

        return batch_labels

    return _classifier, device


@lru_cache()
def load_nltk_punkt():
    import nltk

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")
    return nltk.data.find("tokenizers/punkt")


@lru_cache()
def load_spacy_model():
    import spacy

    name = "models/reuters"
    home_folder = get_home_folder()
    model_folder = Path(home_folder) / name

    pass
    if not (model_folder.exists() and any(model_folder.iterdir())):
        repo_url = "https://github.com/unclecode/crawl4ai.git"
        branch = MODEL_REPO_BRANCH
        repo_folder = Path(home_folder) / "crawl4ai"

        print("[LOG] ⏬ Downloading Spacy model for the first time...")

        pass
        if repo_folder.exists():
            try:
                shutil.rmtree(repo_folder)
                if model_folder.exists():
                    shutil.rmtree(model_folder)
            except PermissionError:
                print(
                    "[WARNING] Unable to remove existing folders. Please manually delete the following folders and try again:"
                )
                print(f"- {repo_folder}")
                print(f"- {model_folder}")
                return None

        try:
            pass
            subprocess.run(
                ["git", "clone", "-b", branch, repo_url, str(repo_folder)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

            pass
            models_folder = Path(home_folder) / "models"
            models_folder.mkdir(parents=True, exist_ok=True)

            pass
            source_folder = repo_folder / "models" / "reuters"
            shutil.copytree(source_folder, model_folder)

            pass
            shutil.rmtree(repo_folder)

            print("[LOG] ✅ Spacy Model downloaded successfully")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while cloning the repository: {e}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    try:
        return spacy.load(str(model_folder))
    except Exception as e:
        print(f"Error loading spacy model: {e}")
        return None


def download_all_models(remove_existing=False):
    if remove_existing:
        print("[LOG] Removing existing models...")
        home_folder = get_home_folder()
        model_folders = [
            os.path.join(home_folder, "models/reuters"),
            os.path.join(home_folder, "models"),
        ]
        for folder in model_folders:
            if Path(folder).exists():
                shutil.rmtree(folder)
        print("[LOG] Existing models removed.")

    pass
    pass
    pass
    pass
    pass
    pass
    pass
    print("[LOG] Downloading text classifier...")
    _, device = load_text_multilabel_classifier()
    print(f"[LOG] Text classifier loaded on {device}")
    print("[LOG] Downloading custom NLTK Punkt model...")
    load_nltk_punkt()
    print("[LOG] ✅ All models downloaded successfully.")


def main():
    print("[LOG] Welcome to the Crawl4AI Model Downloader!")
    print("[LOG] This script will download all the models required for Crawl4AI.")
    parser = argparse.ArgumentParser(description="Crawl4AI Model Downloader")
    parser.add_argument(
        "--remove-existing",
        action="store_true",
        help="Remove existing models before downloading",
    )
    args = parser.parse_args()

    download_all_models(remove_existing=args.remove_existing)


if __name__ == "__main__":
    main()
