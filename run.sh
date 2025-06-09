#!/bin/bash
cd /root/wenku8_novel_list

/usr/bin/python3 main.py >> main.log 2>&1

git add .
if ! git diff --cached --quiet; then
  git commit -m "ci: update novel list"
  git push
fi