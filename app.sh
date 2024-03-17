#!/bin/bash

docker_compose="docker-compose -f docker-compose.yaml"

[ -f config.yaml ] || { echo "Missing config.yaml file. Exiting."; exit 1; }
[ -f variables.py ] || { echo "Missing variables.py file. Exiting."; exit 1; }

if [[ $1 = "start" ]]; then
  echo "Starting Jira Motion Sync..."
	$docker_compose up -d
elif [[ $1 = "stop" ]]; then
	echo "Stopping Jira Motion Sync..."
	$docker_compose stop
elif [[ $1 = "restart" ]]; then
	echo "Restarting Jira Motion Sync..."
  $docker_compose down
  $docker_compose up -d
elif [[ $1 = "down" ]]; then
	echo "Tearing Down Jira Motion Sync..."
	$docker_compose down
elif [[ $1 = "rebuild" ]]; then
	echo "Rebuilding Jira Motion Sync..."
	$docker_compose down --remove-orphans
	$docker_compose build --no-cache
elif [[ $1 = "update" ]]; then
	echo "Updating Jira Motion Sync..."
	$docker_compose down --remove-orphans
	git pull origin master
	$docker_compose build --no-cache
	$docker_compose up -d
elif [[ $1 = "shell" ]]; then
	echo "Entering Jira Motion Sync Shell..."
	docker exec -it jira-motion-sync sh
else
	echo "Unkown or missing command..."
fi