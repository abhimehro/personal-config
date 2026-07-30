with open('.github/workflows/greetings.yml', 'r') as f:
    text = f.read()

search = 'uses: actions/first-interaction@v3'
replace = 'uses: actions/first-interaction@1c4688942c71f71d4f5502a26ea67c331730fa4d # v3'

if search not in text:
    print('Search failed!')
else:
    text = text.replace(search, replace)
    with open('.github/workflows/greetings.yml', 'w') as f:
        f.write(text)
    print('Replaced')
