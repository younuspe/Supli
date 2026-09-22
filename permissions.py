from enum import Enum

class Decision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"

POLICIES = {
    "list_directory": Decision.ALLOW,
    "read_file": Decision.ALLOW,
    "get_platform_info": Decision.ALLOW,
    "write_file": Decision.ASK,
    "run_command": Decision.ASK,
    "git_push": Decision.DENY,
    "git_pull": Decision.DENY,
}

def permission_for(tool_name):
    return POLICIES.get(tool_name, Decision.DENY)

def is_allowed(tool_name):
    return permission_for(tool_name) == Decision.ALLOW

def requires_approval(tool_name):
    return permission_for(tool_name) == Decision.ASK
