file_path = "media-streaming/archive/scripts/infuse-media-server.py"

with open(file_path, "r") as f:
    content = f.read()

# Revert password generation back to original to respect user scope constraint
content = content.replace(
    'password = \'\'.join(secrets.SystemRandom().choices(alphabet, k=16))',
    'password = \'\'.join(secrets.choice(alphabet) for i in range(16))'
)

with open(file_path, "w") as f:
    f.write(content)

print("Reverted password generation to respect PR scope constraint")
