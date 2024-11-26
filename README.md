# Executive Summaries from Linear - Streamlit app

This steamlit app will use an LLM to produce a summary of Linear issues that meet the selected criteria. It's currently setup to use Anthropic, but you could use others by changing the api_key references and client message structure where necessary. The UI allows you to select a team, filter date for completed issues, select status and team members.

## Installation

1. `pip install -r /path/to/requirements.txt`
2. Set your environment variables or create a .streamlit/secrets.toml file with your API keys:
```toml
LINEAR_API_KEY = "linear_api_keu"
 ANTHROPIC_API_KEY = "anthropic_api_key"```
3. `streamlit run linear-summary.py`