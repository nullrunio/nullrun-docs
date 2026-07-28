# AWS Bedrock

Install:

```bash title="shell"
pip install "nullrun[bedrock]"
```

```python title="bedrock_converse.py"
import nullrun
import boto3

nullrun.init(api_key="nr_live_...")

client = boto3.client("bedrock-runtime", region_name="us-east-1")
resp = client.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
)
```

Patched at the `boto3` transport layer; works for every model
hosted on Bedrock (Anthropic, Mistral, Cohere, Meta, AI21, etc.).
The extractor handles both the nested (`response.usage` with
`inputTokens` / `outputTokens`) and the top-level (Anthropic-on-Bedrock
flattens them onto the response body) shapes.

## Test coverage

Per NullRun's testing policy (see the SDK README), AWS Bedrock
patches have **extractor unit tests only** — no full
transport-to-track integration test. The boto3 extractor shape is
exercised by isolated tests, but no multi-roundtrip end-to-end test
confirms the cost actually flows through `/api/v1/track`. The
[Use with Bedrock → Manual tracking](../how-to/custom-tracking.md)
recipe is the recommended pattern for production Bedrock usage.
This is documented per §8 of the source-of-truth positioning.