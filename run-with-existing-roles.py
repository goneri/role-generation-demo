#!/usr/bin/python3

from textwrap import dedent
import re
import urllib3
from pathlib import Path


output_dir = Path("./roles/")


def unwrap(response: str) -> str:
    print(f"RESPONSE={response}")
    m = re.findall(
        "(---\n|```yml\n|```\n)(?P<block>.+?)(```|\Z)",
        response,
        re.MULTILINE | re.DOTALL,
    )
    if m:
        answer = ""
        for i in m:
            block = i[1]
            answer += dedent(block)
        return answer
    else:
        return response

DOCUMENT1_NAME = "roles/haproxy/tasks/main.yml"
DOCUMENT1_CONTENT = """- name: Download and install haproxy
  yum:
    name: haproxy
    state: present

- name: Configure the haproxy cnf file with hosts
  template:
    src: haproxy.cfg.j2
    dest: /etc/haproxy/haproxy.cfg
  notify: restart haproxy

- name: Start the haproxy service
  service:
    name: haproxy
    state: started
    enabled: yes"""
DOCUMENT2_NAME = "roles/apache/tasks/main.yml"
DOCUMENT2_CONTENT = """- name: Install httpd and php
  yum: name={{ item }} state=present
  with_items:
   - httpd
   - php
   - php-mysql

- name: Install web role specific dependencies
  yum: name={{ item }} state=installed
  with_items:
   - git

- name: Start firewalld
  service: name=firewalld state=started enabled=yes

- name: insert firewalld rule for httpd
  firewalld: port={{ httpd_port }}/tcp permanent=true state=enabled immediate=yes

- name: http service state
  service: name=httpd state=started enabled=yes

- name: Configure SELinux to allow httpd to connect to remote database
  seboolean: name=httpd_can_network_connect_db state=true persistent=yes
"""


user_prompt = f"""You are an AI model designed to reuse known Ansible roles that are already available. You reuse these existing files to give the best role-based answer.
[Document]
{DOCUMENT1_NAME}
{DOCUMENT1_CONTENT}
[End]
[Document]
{DOCUMENT2_NAME}
{DOCUMENT2_CONTENT}
[End]
Install haproxy on the localhost machine
"""


role_name = "new_role"
tasks_dir = output_dir / role_name / "tasks"
defaults_dir = output_dir / role_name / "defaults"
tasks_dir.mkdir(parents=True, exist_ok=True)
defaults_dir.mkdir(parents=True, exist_ok=True)
tasks_file = tasks_dir / "main.yml"
defaults_file = defaults_dir / "main.yml"

resp = urllib3.request(
    "POST",
    "http://localhost:11434/api/generate",
    json={
        "model": "granite-code:8b",
        "prompt": user_prompt,
        "stream": False,
        "system": "You are an ansible expert optimized to generate Ansible roles. You only answer with plain tasks/main.yml file that addresses the user request. Prefix your comments with the hash character.",
    },
    timeout=60,
)

content = resp.json()

tasks_main_yml = unwrap(content["response"])
context = content["context"]

resp = urllib3.request(
    "POST",
    "http://localhost:11434/api/generate",
    json={
        "model": "granite-code:8b",
        "prompt": "Prepare the defaults/main.yml for the role.",
        "stream": False,
        "system": "You are an ansible expert optimized to generate Ansible roles. Your goal is to prepare a plain defaults/main.yml file. This file is a list of variables name and value. Prefix your comments with the hash character. Reuse existing roles as much as possible.",
        "context": context,
        #  "format": "json"
    },
    timeout=60,
)

content = resp.json()

defaults_main_yml = unwrap(content["response"])

print(f"Writing {tasks_file} and {defaults_file}")
tasks_file.write_text(tasks_main_yml)
defaults_file.write_text(defaults_main_yml)
