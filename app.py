# **********************************************************
# * CATEGORY  SOFTWARE
# * GROUP     ADMIN
# * AUTHOR    LANCE HAYNIE <LHAYNIE@SCCITY.ORG>
# **********************************************************
# Jira/Motion Bidirectional Syncing
# Copyright Santa Clara City
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os, requests, json, time, yaml, traceback
from datetime import datetime, timedelta
from ratelimit import limits, sleep_and_retry
from variables import assignees


def check_running():
    try:
        lock_file = "/tmp/jiraMotionSync.lock"

        if os.path.exists(lock_file):
            print("The script is already running. Exiting.")
            exit(0)
        else:
            with open(lock_file, "w") as file:
                file.write(str(os.getpid()))
    except Exception as e:
        traceback_message = traceback.format_exc()
        error_report(
            traceback.extract_stack()[-2].name,
            f"An error occurred in 'check_running' function: {e}\n{traceback_message}",
        )
        print(f"An error occurred in 'check_running' function: {e}")


def error_report(function, message):
    url = config["jira-log-api"]
    params = {
        "app": "Jira/Motion Sync",
        "level": "ERR",
        "function": function,
        "msg": str(message),
    }

    response = requests.get(url, params=params)


class JiraClient:
    def __init__(self, api_url, auth):
        self.api_url = api_url
        self.auth = auth

    def fetch_issues(self, jql_query):
        try:
            headers = {"Accept": "application/json"}
            query = {"jql": jql_query}
            response = requests.get(
                self.api_url, headers=headers, params=query, auth=self.auth
            )

            if response.status_code == 200:
                data = json.loads(response.text)
                return data.get("issues", [])
            else:
                print(
                    f"Failed to fetch Jira issues. Status code: {response.status_code}"
                )
                error_report(
                    traceback.extract_stack()[-2].name,
                    f"Failed to fetch Jira issues.\nResponse Content: {response.content}\nStatus code: {response.status_code}",
                )
                return None
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'fetch_issues' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'fetch_issues' method: {e}")
            return None


class MotionClient:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.users = []

    @sleep_and_retry
    @limits(calls=10, period=60)
    def _rate_limited_request(self, method, url, headers=None, **kwargs):
        try:
            default_headers = {"Accept": "application/json", "X-API-Key": self.api_key}
            if headers is not None:
                default_headers.update(headers)

            response = method(url, headers=default_headers, **kwargs)

            if response.status_code == 429:
                print("Rate limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)

                response = method(url, headers=default_headers, **kwargs)

            return response
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in '_rate_limited_request' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in '_rate_limited_request' method: {e}")
            return None

    def fetch_tasks(self, motion_user_id):
        try:
            url = f"{self.api_url}/v1/tasks"

            if motion_user_id == "NA":
                params = {"workspaceId": f"{motion_workspace}"}
            else:
                params = {
                    "workspaceId": f"{motion_workspace}",
                    "assigneeId": f"{motion_user_id}",
                }

            response = self._rate_limited_request(requests.get, url, params=params)

            if response.status_code == 200:
                return response.json().get("tasks", [])
            elif response.status_code == 429:
                print("Rate limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)
                return []
            else:
                print("Failed to fetch Motion tasks.")
                error_report(
                    traceback.extract_stack()[-2].name,
                    f"Failed to fetch Motion tasks.\nResponse Content: {response.content}\nStatus code: {response.status_code}",
                )
                return []
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'fetch_tasks' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'fetch_tasks' method: {e}")
            return []

    def fetch_users(self):
        try:
            if not self.users:
                url = f"{self.api_url}/v1/users"
                headers = {"Accept": "application/json", "X-API-Key": self.api_key}
                params = {"workspaceId": f"{motion_workspace}"}

                response = self._rate_limited_request(requests.get, url, params=params)

                if response.status_code == 200:
                    self.users = response.json().get("users", [])
                elif response.status_code == 429:
                    print("Rate limit exceeded. Waiting for 60 seconds...")
                    time.sleep(60)
                else:
                    print(
                        f"Failed to fetch Motion users. Status code: {response.status_code}"
                    )
                    error_report(
                        traceback.extract_stack()[-2].name,
                        f"Failed to fetch Motion users.\nResponse Content: {response.content}\nStatus code: {response.status_code}",
                    )
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'fetch_users' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'fetch_users' method: {e}")

        return self.users

    def get_user_id(self, username):
        try:
            users = self.fetch_users()
            for user in users:
                if user.get("name") == username:
                    return user.get("id")
            return None
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'get_user_id' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'get_user_id' method: {e}")
            return None

    def update_task_status(self, task_id, status):
        try:
            url = f"{self.api_url}/v1/tasks/{task_id}"

            payload = {"status": status}

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-Key": self.api_key,
            }

            response = self._rate_limited_request(
                requests.patch, url, json=payload, headers=headers
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("Rate limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)
            else:
                print(
                    f"Failed to update task status in Motion. Status code: {response.status_code}"
                )
                error_report(
                    traceback.extract_stack()[-2].name,
                    f"Failed to update task status in Motion.\nResponse Content: {response.content}\nStatus code: {response.status_code}",
                )
                return None
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'update_task_status' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'update_task_status' method: {e}")
            return None

    def update_task_assignee(self, task_id, assignee_id):
        try:
            url = f"{self.api_url}/v1/tasks/{task_id}"

            payload = {"assigneeId": f"{assignee_id}"}

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-Key": self.api_key,
            }

            response = self._rate_limited_request(
                requests.patch, url, json=payload, headers=headers
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("Rate limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)
            elif response.status_code == 404:
                print(f"Task with ID {task_id} not found in Motion. Status code: 404")
                print("Response content:", response.content)
                return None
            else:
                print(
                    f"Failed to update task assignee in Motion. Status code: {response.status_code}"
                )
                print("Response content:", response.content)
                error_report(
                    traceback.extract_stack()[-2].name,
                    f"Failed to fetch Motion users.\nResponse Content: {response.content}\nStatus code: {response.status_code}",
                )
                return None
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'update_task_assignee' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'update_task_assignee' method: {e}")
            return None


class IssueFetcher:
    def __init__(self, jira_client, motion_client):
        self.jira_client = jira_client
        self.motion_client = motion_client
        self.jira_issues = []
        self.motion_tasks = []

    def compare_issues_to_tasks(self, jql_query, assignee_name):
        try:
            motion_user_id = self.motion_client.get_user_id(assignee_name)
            jira_issues = self.jira_client.fetch_issues(jql_query)
            motion_tasks = self.motion_client.fetch_tasks(motion_user_id)

            jira_task_names = set(
                f"{issue['fields']['summary']} ({issue['key']})"
                for issue in jira_issues
            )
            motion_task_names = set(task["name"] for task in motion_tasks)

            jira_not_in_motion = jira_task_names - motion_task_names

            return {
                "jira_not_in_motion": [
                    issue
                    for issue in jira_issues
                    if f"{issue['fields']['summary']} ({issue['key']})"
                    in jira_not_in_motion
                ],
            }
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'compare_issues_to_tasks' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'compare_issues_to_tasks' method: {e}")
            return {"jira_not_in_motion": []}

    def create_task_in_motion(self, issue):
        try:
            assignee = issue["fields"].get("assignee")
            assignee_name = (
                assignee.get("displayName", "Not Assigned")
                if assignee is not None
                else "Not Assigned"
            )

            priority = issue["fields"].get("priority")
            priority_name = (
                priority.get("name", "Medium") if priority is not None else "Medium"
            )

            if priority_name == "Highest":
                priority_name = "ASAP"
            elif priority_name == "Lowest":
                priority_name = "Low"

            motion_user_id = self.motion_client.get_user_id(assignee_name)

            if motion_user_id is None:
                print(f"Failed to find Motion user ID for {assignee_name}")
                return None

            current_time = datetime.utcnow().replace(microsecond=0)
            one_day = timedelta(days=1)
            current_time_plus_1_day = current_time + one_day
            current_time_iso8601 = current_time_plus_1_day.isoformat()

            link = f"{jira_url}/browse/{issue['key']}"
            motion_task_name = f"{issue['fields']['summary']} ({issue['key']})"

            payload = {
                "dueDate": current_time_iso8601,
                "duration": 60,
                "status": "In Progress",
                "autoScheduled": {
                    "startDate": current_time_iso8601,
                    "deadlineType": "NONE",
                    "schedule": "Work Hours",
                },
                "name": motion_task_name,
                "workspaceId": f"{motion_workspace}",
                "description": link,
                "priority": f"{priority_name}",
                "labels": ["JIRA"],
                "assigneeId": motion_user_id,
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-Key": self.motion_client.api_key,
            }

            url = f"{self.motion_client.api_url}/v1/tasks"
            response = requests.post(url, json.dumps(payload), headers=headers)

            time.sleep(5)

            return response.text
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'create_task_in_motion' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'create_task_in_motion' method: {e}")
            return None

    def update_motion_task_status(self, task_id, status):
        try:
            return self.motion_client.update_task_status(task_id, status)
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'update_motion_task_status' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'update_motion_task_status' method: {e}")
            return None

    def task_exists_in_jira(self, task, jira_issues):
        try:
            task_name = task["name"]
            return any(
                task_name == f"{issue['fields']['summary']} ({issue['key']})"
                for issue in jira_issues
            )
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'task_exists_in_jira' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'task_exists_in_jira' method: {e}")
            return False

    def sync_assignees(self, motion_tasks, jira_issues):
        try:
            for motion_task in motion_tasks:
                motion_assignee_list = motion_task.get("assignees", [])
                if motion_assignee_list:
                    motion_assignee = motion_assignee_list[0].get("name")
                else:
                    motion_assignee = None
                motion_task_name = motion_task["name"]

                for jira_issue in jira_issues:
                    jira_assignee = jira_issue["fields"]["assignee"]
                    jira_task_name = (
                        f"{jira_issue['fields']['summary']} ({jira_issue['key']})"
                    )

                    if (
                        motion_task_name == jira_task_name
                        and motion_assignee != jira_assignee
                    ):
                        jira_assignee_name = (
                            jira_assignee.get("displayName", "Not Assigned")
                            if jira_assignee is not None
                            else "Not Assigned"
                        )
                        jira_user_id = self.motion_client.get_user_id(
                            jira_assignee_name
                        )

                        if jira_user_id is not None:
                            self.motion_client.update_task_assignee(
                                motion_task["id"], jira_user_id
                            )
                        else:
                            print(
                                f"Failed to find Jira user ID for '{jira_assignee_name}'"
                            )
                            error_report(
                                traceback.extract_stack()[-2].name,
                                f"Failed to find Jira user ID for '{jira_assignee_name}'",
                            )
        except Exception as e:
            traceback_message = traceback.format_exc()
            error_report(
                traceback.extract_stack()[-2].name,
                f"An error occurred in 'sync_assignees' method: {e}\n{traceback_message}",
            )
            print(f"An error occurred in 'sync_assignees' method: {e}")


def main():
    try:
        check_running()

        jira_client = JiraClient(jira_api_url, jira_auth)
        motion_client = MotionClient(motion_api_url, motion_api_key)

        issue_fetcher = IssueFetcher(jira_client, motion_client)

        all_issues = []
        jira_issues = []

        for assignee_id, assignee_name in assignees.items():
            jql_query = (
                'status not in (Done, "On Hold", Complete, Closed, Resolved, Backlog, Withdrawn, Denied, "To Do") '
                "AND type != Epic "
                f"AND assignee = {assignee_id} "
                "order by updated asc"
            )

            issues_result = issue_fetcher.compare_issues_to_tasks(
                jql_query, assignee_name
            )
            issues = jira_client.fetch_issues(jql_query)
            jira_issues.extend(issues)
            all_issues.extend(issues_result["jira_not_in_motion"])

        if all_issues:
            for issue in all_issues:
                response = issue_fetcher.create_task_in_motion(issue)
                print(response)

        time.sleep(60)

        motion_tasks = motion_client.fetch_tasks("NA")
        motion_tasks = [task for task in motion_tasks]

        for task in motion_tasks:
            motion_task_name = task["name"]

            if not issue_fetcher.task_exists_in_jira(task, jira_issues):
                motion_task_id = task["id"]
                issue_fetcher.update_motion_task_status(motion_task_id, "Completed")

        time.sleep(60)

        issue_fetcher.sync_assignees(motion_tasks, jira_issues)

        time.sleep(60)

        os.remove("/tmp/jiraMotionSync.lock")
    except Exception as e:
        traceback_message = traceback.format_exc()
        error_report(
            traceback.extract_stack()[-2].name,
            f"An error occurred in 'main' function: {e}\n{traceback_message}",
        )
        print(f"An error occurred in 'main' function: {e}")
        print("Restarting in 15 seconds...")
        time.sleep(15)

    print("Sleeping for 15 minutes before the next execution...")
    time.sleep(15 * 60)


if __name__ == "__main__":
    try:
        with open("config.yaml", "r") as config_file:
            config = yaml.safe_load(config_file)

        jira_url = config["jira"]["url"]
        jira_api_url = config["jira"]["api"]
        jira_auth = (config["jira"]["user"], config["jira"]["api_key"])
        motion_api_url = config["motion"]["url"]
        motion_api_key = config["motion"]["api_key"]
        motion_workspace = config["motion"]["workspace_id"]

        while True:
            main()
    except Exception as e:
        traceback_message = traceback.format_exc()
        error_report(
            traceback.extract_stack()[-2].name,
            f"An error occurred in script entry point: {e}\n{traceback_message}",
        )
        print(f"An error occurred in script entry point: {e}")
