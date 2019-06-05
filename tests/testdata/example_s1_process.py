"""Example process file."""


def execute(mp):
    """User defined process."""
    # Reading and writing data works like this:
    with mp.open("primary") as s1_cube:
        if s1_cube.is_empty():
            return "empty"
        data = s1_cube.read_cube(indexes=[1, 2], resampling="cubic")
        data = data.data[0, :, :, :]
    return data
