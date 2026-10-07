from mlx_lm import load, generate

print("Loading model...")
model, tokenizer = load("mlx-community/Mistral-7B-Instruct-v0.2-4bit")

prompt = """<s>[INST] You are a helpful assistant. Return only a JSON object.

Task: Does this text contain a fashion rule?

Text: "Never button the bottom button of a suit jacket"

Return JSON: {"has_rule": true/false, "rule": "the rule text"} [/INST]"""

print("\nGenerating with default params...")
try:
    response = generate(model, tokenizer, prompt=prompt, max_tokens=100, verbose=False)
    print(f"Response: {response}")
except Exception as e:
    print(f"Error: {e}")

print("\nGenerating with temp=0.3...")
try:
    response = generate(model, tokenizer, prompt=prompt, max_tokens=100, temp=0.3, verbose=False)
    print(f"Response: {response}")
except Exception as e:
    print(f"Error: {e}")

print("\nGenerating with temperature=0.3...")
try:
    response = generate(model, tokenizer, prompt=prompt, max_tokens=100, temperature=0.3, verbose=False)
    print(f"Response: {response}")
except Exception as e:
    print(f"Error: {e}")
