# Install

## Python SDK

```bash
pip install nullrun
```

Verify:

```bash
python -c "from nullrun import protect; print('ok')"
```

## API key

Sign in at [app.nullrun.io](https://app.nullrun.io) and create an API key.
Pass it to `init()` or set the `NULLRUN_API_KEY` environment variable:

```bash
export NULLRUN_API_KEY=nr_live_...
```

## Optional extras

```bash
pip install "nullrun[langgraph]"   # LangGraph callback
pip install "nullrun[openai]"      # OpenAI auto-instrumentation
pip install "nullrun[all]"         # all vendor auto-instrumentation
```

## Gateway (self-host)

If you want to run the gateway yourself instead of using the hosted
control plane, see
[`nullrunio/nullrun`](https://github.com/nullrunio/nullrun) and the
[production deployment guide](https://docs.nullrun.io/getting-started/self-host/).
