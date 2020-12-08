import uvicorn


def main():
    uvicorn.run("motley_cue.api:api", host="0.0.0.0", port=8080, log_level="info")


if __name__ == '__main__':
    main()
