# Executive Summaries from Linear - Streamlit app

This steamlit app will use an LLM to produce a summary of Linear issues that meet the selected criteria. It's currently setup to use Anthropic, but you could use others by changing the api_key references and client message structure where necessary. The UI allows you to select a team, filter date for completed issues, select status and team members.

## Installation

1. `pip install -r /path/to/requirements.txt`
2. `streamlit run linear_summary.py`

The initial screen after running the application will require you to input your API keys for Linear and Anthropic