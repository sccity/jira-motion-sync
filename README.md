# Jira/Motion Sync
This program is pretty straightforward. We use Jira for project management, but also use Motion to help automate and manage calendars. This tool takes Jira issues and creates Motion tasks so that they can automatically fit time in to address projects in our calendars. Once the issue in Jira is closed, it will mark it as complete in Motion. It will also look for changes in Jira assignee and update accordingly in Motion.

## INSTALL
```
cd /opt
```
```
sudo git clone https://github.com/sccity/jira-motion-sync.git
```
```
cd jira-motion-sync
```
**Edit config.yaml and variables.py files.**
```
sudo ./app.sh start
```

If you are running Ubuntu, you can also use the jira-motion-sync.service as a systemd service so you do not have to manually start/stop.

## BASIC COMMANDS

Start the Spillman API
```
sudo ./app.sh start
```

Restart Spillman API (useful if things get stuck)
```
sudo ./app.sh restart
```

Stop Jira Motion Sync (temporarily)
```
sudo ./app.sh stop
```

Halt Jira Motion Sync
```
sudo ./app.sh down
```

Update everything to the latest version
```
sudo ./app.sh update
```

Rebuild everything from scratch
```
sudo ./app.sh rebuild
```

## LICENSE
Copyright (c) Santa Clara City UT

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

<http://www.apache.org/licenses/LICENSE-2.0>

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.