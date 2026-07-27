# Embedding runtime compatibility

The Hermes local environment uses:

- `sentence-transformers 2.7.0`
- `transformers 4.57.6`
- `huggingface-hub 0.36.2`

`transformers 4.57.6` requires `huggingface-hub>=0.34,<1.0`.  Do not upgrade
that package to 1.x while this Hermes runtime remains on Transformers 4.x.

The router loads
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` with
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.  Therefore a missing local
model cache fails safely and falls back to explicit semantic examples instead
of downloading a model in a live Hermes conversation.
