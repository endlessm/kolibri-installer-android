from kolibri_android.globals import initialize

initialize()

def main():
    from kolibri_android.server.application import Application
    server_application = Application()
    server_application.run()

if __name__ == "__main__":
    main()
