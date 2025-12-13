# AI Integration Setup

Rosh has built-in AI capabilities using the `prompt` command. This guide shows you how to set up your API keys.

## Quick Start

### 1. Install AI Dependencies

```bash
# Install with OpenAI support
pip install -e ".[ai]"

# Or install just what you need
pip install openai           # For OpenAI (GPT-4, etc.)
pip install anthropic        # For Anthropic (Claude)
```

### 2. Set Up API Key

**Option A: Environment Variable (Recommended)**

```bash
# Add to your ~/.bashrc, ~/.zshrc, or ~/.profile
export OPENAI_API_KEY="sk-your-key-here"

# Or for Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**Option B: Config File**

Create `~/.rosh/config.json`:

```json
{
  "ai": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "openai_api_key": "sk-your-key-here"
  }
}
```

### 3. Test It!

```bash
rosh -c 'prompt "Say hello in a creative way"'
```

## Using AI in Rosh

### 1. Text Generation (`prompt`)

```rosh
# Simple prompt (prints to stdout)
prompt "Explain recursion in one sentence"

# Store result in variable
prompt "Generate a random number between 1 and 100" into lucky_number
print lucky_number
```

### 2. Code Generation (`prompt exec`) 🔥

**This is the killer feature!** AI generates actual Rosh code that executes:

```rosh
# AI writes and runs code automatically
prompt exec "Create a player with health 100 and name Hero"
# → AI generates: create object player / set health to 100 / set name to "Hero" / end
# → Code executes automatically
# → player variable now exists!

print player  # Works!
```

### 3. Code Execution (`eval`)

Execute Rosh code from strings:

```rosh
create string code as "create number x as 42"
eval code
print x  # → 42
```

### With Context

```rosh
# Create some data
create object player
  set name to "Hero"
  set health to 85
  set level to 5
end

# Ask AI using the player data
prompt "Based on the player's stats, suggest a difficulty level" using player into difficulty

print difficulty
```

### Multiple Variables

```rosh
create number score as 1500
create string mood as "excited"

prompt "Generate a congratulations message" using score mood into message
print message
```

## Supported Providers

### OpenAI (Default)

- Models: `gpt-4o`, `gpt-4o-mini`, `gpt-4`, `gpt-3.5-turbo`
- Get key: https://platform.openai.com/api-keys
- Env var: `OPENAI_API_KEY`

**Config:**
```json
{
  "ai": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "openai_api_key": "sk-..."
  }
}
```

### Anthropic (Claude)

- Models: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- Get key: https://console.anthropic.com/
- Env var: `ANTHROPIC_API_KEY`

**Config:**
```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "anthropic_api_key": "sk-ant-..."
  }
}
```

## Config Reference

Full `~/.rosh/config.json` example:

```json
{
  "ai": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "openai_api_key": "sk-...",
    "anthropic_api_key": "sk-ant-..."
  }
}
```

**Options:**
- `provider`: AI provider name (`"openai"`, `"anthropic"`)
- `model`: Model name (provider-specific)
- `temperature`: Creativity level (0.0 to 1.0)
- `max_tokens`: Maximum response length
- `{provider}_api_key`: API key for each provider

## Examples

See `examples/ai-*.rosh` for complete examples:
- `examples/ai-hello.rosh` - Simple prompt
- `examples/ai-context.rosh` - Using context variables
- `examples/ai-game.rosh` - Interactive game with AI

## Troubleshooting

**Error: "No API key found"**
- Set environment variable or config file
- Reload your shell after setting env var

**Error: "openai package not installed"**
- Run: `pip install -e ".[ai]"`

**Error: "AI prompt failed: ..."**
- Check your API key is valid
- Verify you have credits/quota remaining
- Check your internet connection

## Security

**Never commit API keys to git!**
- Use environment variables
- Or `~/.rosh/config.json` (already gitignored)
- Never hardcode keys in `.rosh` files

## Next Steps

- Try the examples: `rosh examples/ai-hello.rosh`
- Read the full spec: `spec/rosh_full_spec_v0_1.md`
- Join the community: [GitHub Discussions](#)
