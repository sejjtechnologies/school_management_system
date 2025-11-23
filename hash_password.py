from werkzeug.security import generate_password_hash

def main():
    raw_password = "sejjtech"
    hashed_password = generate_password_hash(raw_password)
    print("Hashed password for 'sejjtech':")
    print(hashed_password)

if __name__ == "__main__":
    main()