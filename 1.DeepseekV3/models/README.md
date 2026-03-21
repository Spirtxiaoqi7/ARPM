# Models Directory

This directory contains the embedding models for ARPM system.

## Structure

```
models/
└── shibing624/
    └── text2vec-base-chinese/     # Chinese text embedding model
        ├── README.md              # This file
        └── [model files...]       # Downloaded separately
```

## Setup

### Automatic Download (Recommended)

The system will automatically download the model on first run if not present.

### Manual Download

```bash
cd models/shibing624/text2vec-base-chinese

# Option 1: Using huggingface-cli
huggingface-cli download shibing624/text2vec-base-chinese --local-dir . --local-dir-use-symlinks False

# Option 2: Using Python
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('shibing624/text2vec-base-chinese', cache_folder='.')"

# Option 3: Download from browser
# Visit: https://huggingface.co/shibing624/text2vec-base-chinese/tree/main
# Download all files and place them in this directory
```

## Model Information

- **Model**: shibing624/text2vec-base-chinese
- **Type**: Sentence Transformer
- **Language**: Chinese
- **Dimension**: 768
- **Framework**: PyTorch

## License

The model follows the original license from shibing624.
