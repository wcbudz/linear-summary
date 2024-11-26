import os
from datetime import datetime, timedelta
import streamlit as st
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from anthropic import Anthropic

class LinearExecutiveSummary:
    def __init__(self, linear_api_key, anthropic_api_key):
        self.linear_client = Client(
            transport=RequestsHTTPTransport(
                url='https://api.linear.app/graphql',
                headers={'Authorization': linear_api_key}
            )
        )
        self.anthropic_client = Anthropic(api_key=anthropic_api_key)

    def get_teams(self):
        query = gql("""
        query {
          teams {
            nodes {
              id
              name
              key
              states {
                nodes {
                  id
                  name
                  type
                }
              }
            }
          }
        }
        """)
        result = self.linear_client.execute(query)
        return result['teams']['nodes']

    def get_team_members(self, team_id=None):
        query = gql("""
        query {
          users {
            nodes {
              id
              name
              email
            }
          }
        }
        """)
        result = self.linear_client.execute(query)
        return result['users']['nodes']

    def get_filtered_issues(self, team_id, completed_before=None, completed_after=None, status_ids=None, assignee_ids=None):
        filters = [f'team: {{ id: {{ eq: "{team_id}" }} }}']
        
        # Handle completed date filters
        if completed_before or completed_after:
            completed_conditions = []
            if completed_before:
                completed_conditions.append(f'lte: "{completed_before.isoformat()}"')
            if completed_after:
                completed_conditions.append(f'gte: "{completed_after.isoformat()}"')
            
            filters.append(f'completedAt: {{ {", ".join(completed_conditions)} }}')
        
        if status_ids:
            status_filter = ', '.join([f'"{id}"' for id in status_ids])
            filters.append(f'state: {{ id: {{ in: [{status_filter}] }} }}')
        
        if assignee_ids:
            assignee_filter = ', '.join([f'"{id}"' for id in assignee_ids])
            filters.append(f'assignee: {{ id: {{ in: [{assignee_filter}] }} }}')
        
        filter_string = ', '.join(filters)
        
        query = gql(f"""
        query {{
          issues(
            filter: {{ {filter_string} }}
          ) {{
            nodes {{
              title
              identifier
              state {{
                name
                type
              }}
              priority
              completedAt
              description
              assignee {{
                name
                email
              }}
              labels {{ nodes {{ name }} }}
              history(first: 10) {{
                nodes {{
                  fromState {{ name }}
                  toState {{ name }}
                  updatedAt
                }}
              }}
            }}
          }}
        }}
        """)

        try:
            result = self.linear_client.execute(query)
            return result['issues']['nodes']
        except Exception as e:
            st.error(f"GraphQL Query: {query}")
            raise e

    def generate_summary(self, issues):
        # Prepare the data for Claude
        issues_text = ""
        for issue in issues:
            status_changes = "\n".join([
                f"- Changed from {h['fromState']['name']} to {h['toState']['name']} on {h['updatedAt']}"
                for h in issue['history']['nodes'] if h['fromState'] and h['toState']
            ])
            
            labels = ", ".join([label['name'] for label in issue['labels']['nodes']])
            assignee = issue['assignee']['name'] if issue['assignee'] else "Unassigned"
            completed_date = issue.get('completedAt', 'Not completed')
            
            issues_text += f"""
Issue: {issue['identifier']} - {issue['title']}
Assignee: {assignee}
Status: {issue['state']['name']}
Priority: {issue['priority']}
Completed: {completed_date}
Labels: {labels}
Description: {issue['description']}
Status Changes:
{status_changes}
---
"""

        prompt = f"""Please analyze these Linear issues and create a concise executive summary. 
Focus on:
1. Key accomplishments and progress
2. Notable status changes or blockers
3. Emerging trends or patterns
4. High-priority items requiring attention
5. Team member contributions and workload distribution

Issues:
{issues_text}

Please format the summary in clear, business-appropriate language suitable for executives."""

        message = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are an expert at analyzing project management data and creating executive summaries.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return message.content

def initialize_session_state():
    if 'api_keys_submitted' not in st.session_state:
        st.session_state.api_keys_submitted = False
    if 'linear_api_key' not in st.session_state:
        st.session_state.linear_api_key = None
    if 'anthropic_api_key' not in st.session_state:
        st.session_state.anthropic_api_key = None

def validate_api_keys(linear_key, anthropic_key):
    try:
        # Test Linear API key
        test_client = Client(
            transport=RequestsHTTPTransport(
                url='https://api.linear.app/graphql',
                headers={'Authorization': linear_key}
            )
        )
        test_query = gql("""
            query { viewer { id } }
        """)
        test_client.execute(test_query)
        
        # Test Anthropic API key
        test_anthropic = Anthropic(api_key=anthropic_key)
        test_anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=10,
            messages=[{"role": "user", "content": "test"}]
        )
        return True, None
    except Exception as e:
        return False, str(e)

def api_key_form():
    st.title("Linear Executive Summary Generator")
    
    with st.form("api_key_form"):
        st.write("Please enter your API keys to continue:")
        
        linear_key = st.text_input("Linear API Key", type="password")
        anthropic_key = st.text_input("Anthropic API Key", type="password")
        
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            if linear_key and anthropic_key:
                success, error = validate_api_keys(linear_key, anthropic_key)
                if success:
                    st.session_state.linear_api_key = linear_key
                    st.session_state.anthropic_api_key = anthropic_key
                    st.session_state.api_keys_submitted = True
                    st.rerun()
                else:
                    st.error(f"Error validating API keys: {error}")
            else:
                st.error("Please provide both API keys.")

def main_app():
    summarizer = LinearExecutiveSummary(
        st.session_state.linear_api_key,
        st.session_state.anthropic_api_key
    )
    
    # Add a way to reset API keys if needed
    if st.sidebar.button("Reset API Keys"):
        st.session_state.api_keys_submitted = False
        st.session_state.linear_api_key = None
        st.session_state.anthropic_api_key = None
        st.rerun()

    st.title("Linear Executive Summary Generator")

    # Team selector
    st.subheader("Select Team")
    teams = summarizer.get_teams()
    team_options = [(team['id'], f"{team['key']} - {team['name']}") for team in teams]
    selected_team = st.selectbox(
        "Team",
        options=team_options,
        format_func=lambda x: x[1]
    )
    
    if not selected_team:
        st.warning("Please select a team to continue.")
        return

    selected_team_id = selected_team[0]
    
    # Get the selected team's data
    selected_team_data = next((team for team in teams if team['id'] == selected_team_id), None)

    # Date filters
    st.subheader("Completion Date Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        use_after_date = st.checkbox("Filter by Completed After")
        completed_after = None
        if use_after_date:
            completed_after = st.date_input(
                "Completed After",
                value=datetime.now() - timedelta(days=30)
            )

    with col2:
        use_before_date = st.checkbox("Filter by Completed Before")
        completed_before = None
        if use_before_date:
            completed_before = st.date_input(
                "Completed Before",
                value=datetime.now()
            )

    # Status selector - now using team-specific states
    st.subheader("Status Filters")
    if selected_team_data:
        statuses = selected_team_data['states']['nodes']
        status_options = [(status['id'], status['name']) for status in statuses]
        selected_statuses = st.multiselect(
            "Select Statuses",
            options=status_options,
            format_func=lambda x: x[1]
        )
        selected_status_ids = [status[0] for status in selected_statuses]
    
    # Team member selector
    st.subheader("Assignee Filters")
    team_members = summarizer.get_team_members(selected_team_id)
    selected_members = st.multiselect(
        "Select Team Members",
        options=[(member['id'], member['name']) for member in team_members],
        format_func=lambda x: x[1]
    )
    selected_member_ids = [member[0] for member in selected_members]

    if st.button("Generate Summary"):
        with st.spinner("Fetching issues and generating summary..."):
            try:
                # Convert dates to datetime with time components
                completed_before_dt = datetime.combine(completed_before, datetime.max.time()) if completed_before else None
                completed_after_dt = datetime.combine(completed_after, datetime.min.time()) if completed_after else None
                
                issues = summarizer.get_filtered_issues(
                    team_id=selected_team_id,
                    completed_before=completed_before_dt,
                    completed_after=completed_after_dt,
                    status_ids=selected_status_ids if selected_status_ids else None,
                    assignee_ids=selected_member_ids if selected_member_ids else None
                )
                
                if not issues:
                    st.warning("No issues found matching the selected criteria.")
                    return
                
                # Preview the raw data
                if st.checkbox("Show raw data"):
                    st.json(issues)
                
                summary = summarizer.generate_summary(issues)
                
                # Extract the text content from the response
                if isinstance(summary, list) and len(summary) > 0:
                    summary_text = summary[0].text if hasattr(summary[0], 'text') else str(summary[0])
                else:
                    summary_text = str(summary)
                
                st.subheader("Executive Summary")
                st.markdown(summary_text)
                
                # Add download button for the summary
                st.download_button(
                    label="Download Summary",
                    data=summary_text,
                    file_name=f"linear_summary_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
                
                # Display issue count
                st.info(f"Summary generated from {len(issues)} issues.")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.error("Full error details:", exc_info=True)

def main():
    initialize_session_state()
    
    if not st.session_state.api_keys_submitted:
        api_key_form()
    else:
        main_app()

if __name__ == "__main__":
    main()