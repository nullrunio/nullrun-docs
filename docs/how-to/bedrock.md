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
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
)
```

Patched at the `boto3` transport layer; works for every model
hosted on Bedrock (Anthropic, Mistral, Cohere, Meta, AI21, etc.).
The extractor handles both the nested (`response.usage` with
`inputTokens` / `outputTokens`) and the top-level (Anthropic-on-Bedrock
flattens them onto the response body) shapes.

The
[Use with Bedrock → Manual tracking](../how-to/custom-tracking.md)
recipe is the recommended pattern for production Bedrock usage.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md#test-coverage-caveat)
