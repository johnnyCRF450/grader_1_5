"""
ML Algorithm knowledge base for Assignment 1.5.
Used as ground-truth reference by all agents for classification accuracy assessment.
"""

import pandas as pd

ALGORITHM_KNOWLEDGE_BASE = pd.DataFrame([
    # ── Supervised / Tabular ──────────────────────────────────────────────────
    {"algorithm": "Linear Regression",        "learning_type": "Supervised",   "domains": ["Tabular Data"],                  "task": "Regression",       "key_concept": "Fits a linear relationship between features and a continuous target. Minimizes mean squared error.", "examples": "House price prediction, sales forecasting, risk scoring"},
    {"algorithm": "Logistic Regression",      "learning_type": "Supervised",   "domains": ["Tabular Data"],                  "task": "Classification",   "key_concept": "Extends linear regression with a sigmoid function to output class probabilities.", "examples": "Spam detection, loan approval, medical diagnosis"},
    {"algorithm": "Decision Tree",            "learning_type": "Supervised",   "domains": ["Tabular Data"],                  "task": "Classification/Regression", "key_concept": "Recursively splits data on feature thresholds to form a tree of if-then rules.", "examples": "Credit scoring, medical triage, customer churn"},
    {"algorithm": "Random Forest",            "learning_type": "Supervised",   "domains": ["Tabular Data"],                  "task": "Classification/Regression", "key_concept": "Ensemble of decision trees trained on random feature subsets; averages predictions to reduce overfitting.", "examples": "Fraud detection, stock prediction, disease diagnosis"},
    {"algorithm": "Gradient Boosting (XGBoost/LightGBM)", "learning_type": "Supervised", "domains": ["Tabular Data"],       "task": "Classification/Regression", "key_concept": "Builds trees sequentially, each correcting errors of the previous. State-of-the-art for structured data.", "examples": "Kaggle competitions, click-through rate prediction, ranking"},
    {"algorithm": "Support Vector Machine",   "learning_type": "Supervised",   "domains": ["Tabular Data", "Computer Vision"], "task": "Classification", "key_concept": "Finds the hyperplane maximizing the margin between classes. Kernel trick handles non-linear boundaries.", "examples": "Image classification, text categorization, bioinformatics"},
    # ── Unsupervised / Tabular ────────────────────────────────────────────────
    {"algorithm": "K-means Clustering",       "learning_type": "Unsupervised", "domains": ["Tabular Data"],                  "task": "Clustering",       "key_concept": "Assigns data points to K clusters by minimizing distance to cluster centroids. Iterates until convergence.", "examples": "Customer segmentation, document clustering, anomaly detection"},
    {"algorithm": "Principal Component Analysis (PCA)", "learning_type": "Unsupervised", "domains": ["Tabular Data", "Computer Vision"], "task": "Dimensionality Reduction", "key_concept": "Projects data onto orthogonal axes capturing maximum variance. Reduces dimensionality while preserving structure.", "examples": "Feature compression, visualization, noise reduction"},
    {"algorithm": "DBSCAN",                   "learning_type": "Unsupervised", "domains": ["Tabular Data"],                  "task": "Clustering",       "key_concept": "Density-based clustering that groups tightly packed points and marks outliers as noise. No fixed K required.", "examples": "Geospatial clustering, outlier detection, social network analysis"},
    # ── Computer Vision ───────────────────────────────────────────────────────
    {"algorithm": "Convolutional Neural Network (CNN)", "learning_type": "Supervised", "domains": ["Computer Vision"],       "task": "Image Classification/Detection", "key_concept": "Uses convolutional filters to detect spatial features (edges, textures, objects) hierarchically.", "examples": "Image classification, object detection (YOLO), medical imaging"},
    {"algorithm": "ResNet / VGG / EfficientNet", "learning_type": "Supervised", "domains": ["Computer Vision"],             "task": "Image Classification", "key_concept": "Deep CNN architectures with skip connections (ResNet) or efficient scaling (EfficientNet) for transfer learning.", "examples": "Face recognition, ImageNet classification, autonomous driving"},
    {"algorithm": "YOLO (Object Detection)",  "learning_type": "Supervised",   "domains": ["Computer Vision"],              "task": "Object Detection", "key_concept": "Single-pass real-time object detection predicting bounding boxes and class probabilities simultaneously.", "examples": "Self-driving cars, surveillance, robotics"},
    # ── NLP ───────────────────────────────────────────────────────────────────
    {"algorithm": "Transformer / BERT",       "learning_type": "Supervised",   "domains": ["NLP"],                          "task": "Language Understanding", "key_concept": "Self-attention mechanism captures long-range token relationships. BERT uses bidirectional context for encoding.", "examples": "Sentiment analysis, question answering, named entity recognition"},
    {"algorithm": "GPT (Large Language Model)", "learning_type": "Supervised (self-supervised)", "domains": ["NLP", "Generative AI"], "task": "Text Generation", "key_concept": "Autoregressive transformer predicting the next token. Scales to billions of parameters via self-supervised pre-training.", "examples": "ChatGPT, code generation, summarization, translation"},
    {"algorithm": "Word2Vec / GloVe",         "learning_type": "Unsupervised", "domains": ["NLP"],                          "task": "Word Embeddings", "key_concept": "Maps words to dense vectors preserving semantic relationships. Similar words cluster in vector space.", "examples": "Semantic search, recommendation systems, text classification"},
    # ── Generative AI ─────────────────────────────────────────────────────────
    {"algorithm": "Generative Adversarial Network (GAN)", "learning_type": "Unsupervised", "domains": ["Generative AI", "Computer Vision"], "task": "Image/Data Generation", "key_concept": "Generator and discriminator networks compete: generator creates synthetic data, discriminator detects fakes.", "examples": "DeepFake, StyleGAN portraits, data augmentation, art generation"},
    {"algorithm": "Diffusion Model (Stable Diffusion)", "learning_type": "Unsupervised", "domains": ["Generative AI", "Computer Vision"], "task": "Image Generation", "key_concept": "Learns to reverse a noise-addition process. Denoises random noise step-by-step guided by text prompts.", "examples": "Stable Diffusion, DALL-E, Midjourney, image editing"},
    {"algorithm": "Variational Autoencoder (VAE)", "learning_type": "Unsupervised", "domains": ["Generative AI", "Tabular Data"], "task": "Generation/Compression", "key_concept": "Encodes data into a probabilistic latent space; samples from this space to generate novel outputs.", "examples": "Image synthesis, anomaly detection, drug discovery"},
    {"algorithm": "Recurrent Neural Network / LSTM", "learning_type": "Supervised", "domains": ["NLP", "Tabular Data"],     "task": "Sequence Modeling", "key_concept": "Processes sequences step-by-step with hidden state memory. LSTM adds gating to handle long-range dependencies.", "examples": "Time series forecasting, speech recognition, machine translation"},
]).set_index("algorithm")

DOMAIN_DESCRIPTIONS = {
    "Tabular Data": "Structured data in rows/columns (spreadsheets, databases). Best served by tree-based models and classical ML.",
    "Computer Vision": "Image and video understanding. Dominated by CNNs and Vision Transformers (ViT).",
    "NLP": "Text and language processing. Transformers (BERT, GPT) are the current standard.",
    "Generative AI": "Creating new content (images, text, audio). Uses GANs, Diffusion models, and LLMs.",
}

LEARNING_TYPE_DESCRIPTIONS = {
    "Supervised": "Trained on labeled data (input → known output). Goal: learn a mapping to predict labels on new data.",
    "Unsupervised": "Trained on unlabeled data. Goal: discover hidden structure, patterns, or representations.",
    "Semi-supervised": "Uses a small amount of labeled data plus large amounts of unlabeled data.",
    "Self-supervised": "Creates labels from the data itself (e.g., predict masked words). Used in LLM pre-training.",
    "Reinforcement Learning": "Agent learns by taking actions in an environment and receiving rewards/penalties.",
}

MINIMUM_ALGORITHMS_REQUIRED = 8


def get_knowledge_base_string() -> str:
    lines = [
        "ML ALGORITHM KNOWLEDGE BASE (ground truth for classification accuracy assessment)",
        f"Total algorithms in reference: {len(ALGORITHM_KNOWLEDGE_BASE)}",
        f"Minimum required in student submission: {MINIMUM_ALGORITHMS_REQUIRED}",
        "",
        "Correct classifications (algorithm → learning type → primary domain):",
    ]
    for alg, row in ALGORITHM_KNOWLEDGE_BASE.iterrows():
        domains = ", ".join(row["domains"])
        lines.append(f"  {alg}: {row['learning_type']} | {domains} | {row['task']}")
    lines += [
        "",
        "Domain descriptions:",
    ]
    for domain, desc in DOMAIN_DESCRIPTIONS.items():
        lines.append(f"  {domain}: {desc}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_knowledge_base_string())
    print(f"\nTotal algorithms: {len(ALGORITHM_KNOWLEDGE_BASE)}")
