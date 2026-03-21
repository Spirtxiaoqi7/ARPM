# text2vec-base-chinese Model

This directory should contain the `text2vec-base-chinese` model files.

## Download

Download the model from HuggingFace:

```bash
# Install huggingface-cli
pip install huggingface-hub

# Download model
huggingface-cli download shibing624/text2vec-base-chinese --local-dir . --local-dir-use-symlinks False
```

Or manually download from: https://huggingface.co/shibing624/text2vec-base-chinese

## Required Files

After download, this directory should contain:
- `config.json`
- `pytorch_model.bin` (main model weights)
- `vocab.txt`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `modules.json`
- `sentence_bert_config.json`

## Note

Model files are excluded from Git due to size (>25MB). Users must download the model separately after cloning the repository.
