# Fine-tuning (Scaffold)

This project already uses prompt+style guides to enforce the Steven Bartlett + Alex Hormozi-inspired voice.
If you want deeper consistency, add fine-tuning with your preferred provider. This folder gives you a
provider-agnostic data pipeline and a place to store training outputs.

## 1) Collect training pairs

Create a JSONL file with `input` and `output` for each example. Focus on transforming real news inputs
into the target voice (short, tactical, emotionally resonant, action-oriented).

Example line:

```json
{"input":"Summarize this article about a new AV safety regulation...","output":"<h2>Safety Rules Just Got Teeth</h2>..."}
```

Aim for 100+ examples if you want strong consistency.

## 2) Build datasets

Use the script to build provider-agnostic pairs and a generic chat JSONL format:

```bash
python NewsletterAiAgent/scripts/prepare_finetune_data.py \
  --style-examples NewsletterAiAgent/style_examples/bartlett_hormozi.json \
  --pairs NewsletterAiAgent/training/raw_pairs.jsonl
```

Outputs:

- `NewsletterAiAgent/training/finetune_pairs.jsonl`
- `NewsletterAiAgent/training/finetune_chat.jsonl`

## 3) Train with your provider

Use the dataset format your provider requires. If they accept chat JSONL with `messages`, you can use
`finetune_chat.jsonl`. Otherwise, adapt `finetune_pairs.jsonl` to the required schema.

## 4) Wire the model into the app

Once you have a fine-tuned model ID or local model name:

- If you’re using Ollama, set `OLLAMA_MODEL` in `.env` to the fine-tuned model name.
- If you’re using another provider, add a new provider handler in `NewsletterAiAgent/src/newsletter/llm.py` and
  set `LLM_PROVIDER` accordingly.

## Notes

- Keep HTML tags consistent with the app’s constraints: `<h2>`, `<h3>`, `<p>`, `<ul>`, `<li>`, `<a>`, `<img>`.
- Do not include the literal words “Source” or “Sources” in outputs.
