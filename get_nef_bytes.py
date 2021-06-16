def get_nef_bytes(path: str, output: callable = print):
    with open(path, 'rb') as f:
        content = f.read()
        output(content)

if __name__ == '__main__':
    get_nef_bytes('rToken.nef')