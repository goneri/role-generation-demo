#!/usr/bin/python3

from textwrap import dedent
import re
import urllib3
from pathlib import Path


user_prompt = "Prepare a VPC, create the subnets, and deploy an ec2-instance"

output_dir = Path("./roles/")


def unwrap(response: str) -> str:
    # print(f"RESPONSE={response}")
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
        "system": "You are an ansible expert optimized to generate Ansible roles. Your goal is to prepare a plain defaults/main.yml file. This file is a list of variables name and value. Prefix your comments with the hash character.",
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
