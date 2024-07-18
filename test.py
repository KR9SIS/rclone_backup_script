string = "/this/is/a/parent//"

index = string.rfind("/", 0, -1)
parent_dir = string[
    0 : index + 1
]  # TODO Change this line to actually get parent directory

print()
print((string))
print(parent_dir)
