from mapchete_hub.commands import execute, index


command_funcs = {
    "execute": execute.run,
    "index": index.run,
}
command_funcs_paths = {
    "execute": "mapchete_hub.commands.execute.run",
    "index": "mapchete_hub.commands.index.run",
}


def command_func(command_name):
    """Return comand function."""
    return command_funcs[command_name.replace("_worker", "")]


def command_func_path(command_name):
    """Return comand function."""
    return command_funcs_paths[command_name.replace("_worker", "")]
